#!/usr/bin/env node
/**
 * TypeScript Compiler API query tool.
 * Single-shot execution: runs query, outputs JSON, exits.
 * No persistent process, no orphan risk.
 *
 * Usage:
 *   node ts-query.js '{"command": "sig", "file": "src/auth.ts"}'
 *   node ts-query.js '{"command": "map", "path": ".", "top": 10}'
 *   node ts-query.js '{"command": "refs", "file": "src/auth.ts", "line": 10, "column": 5}'
 *
 * Part of DX-78: TypeScript Compiler Integration.
 */

const ts = require('typescript');
const fs = require('fs');
const path = require('path');

// Parse query from command line
let query;
try {
    query = JSON.parse(process.argv[2] || '{}');
} catch (e) {
    console.error(JSON.stringify({
        error: 'Invalid JSON input',
        message: e.message
    }));
    process.exit(1);
}

/**
 * Find tsconfig.json and create a TypeScript program.
 */
function createProgram(projectPath) {
    const configPath = ts.findConfigFile(
        projectPath,
        ts.sys.fileExists,
        'tsconfig.json'
    );

    if (!configPath) {
        console.error(JSON.stringify({ error: 'tsconfig.json not found' }));
        process.exit(1);
    }

    const configFile = ts.readConfigFile(configPath, ts.sys.readFile);
    if (configFile.error) {
        console.error(JSON.stringify({ error: 'Failed to read tsconfig.json' }));
        process.exit(1);
    }

    const parsed = ts.parseJsonConfigFileContent(
        configFile.config,
        ts.sys,
        path.dirname(configPath)
    );

    return ts.createProgram(parsed.fileNames, parsed.options);
}

/**
 * Get class/function members recursively.
 */
function getMembers(node, checker, sourceFile) {
    const members = [];

    if (ts.isClassDeclaration(node) && node.members) {
        for (const member of node.members) {
            if (ts.isMethodDeclaration(member) || ts.isPropertyDeclaration(member)) {
                const name = member.name ? member.name.getText(sourceFile) : '<anonymous>';
                const symbol = checker.getSymbolAtLocation(member.name || member);
                let signature = '';

                if (symbol) {
                    const type = checker.getTypeOfSymbolAtLocation(symbol, member);
                    signature = checker.typeToString(type);
                }

                const pos = sourceFile.getLineAndCharacterOfPosition(member.pos);
                members.push({
                    name,
                    kind: ts.isMethodDeclaration(member) ? 'method' : 'property',
                    signature,
                    line: pos.line + 1
                });
            }
        }
    }

    return members;
}

/**
 * Extract JSDoc @pre/@post comments.
 */
function extractContracts(node, sourceFile) {
    const contracts = { pre: [], post: [] };
    const jsDocs = ts.getJSDocTags(node);

    for (const tag of jsDocs) {
        const tagName = tag.tagName.getText();
        const comment = typeof tag.comment === 'string'
            ? tag.comment
            : tag.comment?.map(c => c.text).join('') || '';

        if (tagName === 'pre') {
            contracts.pre.push(comment);
        } else if (tagName === 'post') {
            contracts.post.push(comment);
        }
    }

    return contracts;
}

/**
 * Command: sig - Extract signatures from a file.
 */
function outputSignatures(filePath) {
    const projectPath = path.dirname(filePath);
    const program = createProgram(projectPath);
    const checker = program.getTypeChecker();
    const sourceFile = program.getSourceFile(path.resolve(filePath));

    if (!sourceFile) {
        console.log(JSON.stringify({ file: filePath, symbols: [], error: 'File not found in program' }));
        return;
    }

    const symbols = [];

    function visit(node) {
        if (ts.isFunctionDeclaration(node) && node.name) {
            const name = node.name.getText(sourceFile);
            const symbol = checker.getSymbolAtLocation(node.name);
            const type = symbol ? checker.getTypeOfSymbolAtLocation(symbol, node) : null;
            const pos = sourceFile.getLineAndCharacterOfPosition(node.pos);
            const contracts = extractContracts(node, sourceFile);

            symbols.push({
                name,
                kind: 'function',
                signature: type ? checker.typeToString(type) : '',
                line: pos.line + 1,
                contracts
            });
        } else if (ts.isClassDeclaration(node) && node.name) {
            const name = node.name.getText(sourceFile);
            const pos = sourceFile.getLineAndCharacterOfPosition(node.pos);
            const members = getMembers(node, checker, sourceFile);

            symbols.push({
                name,
                kind: 'class',
                signature: `class ${name}`,
                line: pos.line + 1,
                members
            });
        } else if (ts.isInterfaceDeclaration(node) && node.name) {
            const name = node.name.getText(sourceFile);
            const pos = sourceFile.getLineAndCharacterOfPosition(node.pos);

            symbols.push({
                name,
                kind: 'interface',
                signature: `interface ${name}`,
                line: pos.line + 1
            });
        } else if (ts.isTypeAliasDeclaration(node) && node.name) {
            const name = node.name.getText(sourceFile);
            const pos = sourceFile.getLineAndCharacterOfPosition(node.pos);

            symbols.push({
                name,
                kind: 'type',
                signature: `type ${name}`,
                line: pos.line + 1
            });
        } else if (ts.isVariableStatement(node)) {
            for (const decl of node.declarationList.declarations) {
                if (ts.isIdentifier(decl.name)) {
                    const name = decl.name.getText(sourceFile);
                    const symbol = checker.getSymbolAtLocation(decl.name);
                    const type = symbol ? checker.getTypeOfSymbolAtLocation(symbol, decl) : null;
                    const pos = sourceFile.getLineAndCharacterOfPosition(decl.pos);

                    // Only include exported or significant declarations
                    const isExported = node.modifiers?.some(m => m.kind === ts.SyntaxKind.ExportKeyword);
                    const isFunctionLike = decl.initializer && (
                        ts.isArrowFunction(decl.initializer) || ts.isFunctionExpression(decl.initializer)
                    );
                    if (isExported || isFunctionLike) {
                        symbols.push({
                            name,
                            kind: 'const',
                            signature: type ? checker.typeToString(type) : '',
                            line: pos.line + 1
                        });
                    }
                }
            }
        }

        ts.forEachChild(node, visit);
    }

    visit(sourceFile);
    console.log(JSON.stringify({ file: filePath, symbols }));
}

/**
 * Command: map - Get symbol map with reference counts.
 */
function outputSymbolMap(projectPath, topN) {
    const program = createProgram(projectPath);
    const checker = program.getTypeChecker();
    const allSymbols = [];

    // Collect all symbols from all source files
    for (const sourceFile of program.getSourceFiles()) {
        // Skip node_modules and declaration files
        if (sourceFile.isDeclarationFile || sourceFile.fileName.includes('node_modules')) {
            continue;
        }

        const relativePath = path.relative(projectPath, sourceFile.fileName);

        function visit(node) {
            let symbolInfo = null;

            if (ts.isFunctionDeclaration(node) && node.name) {
                const name = node.name.getText(sourceFile);
                const pos = sourceFile.getLineAndCharacterOfPosition(node.pos);
                symbolInfo = { name, kind: 'function', file: relativePath, line: pos.line + 1 };
            } else if (ts.isClassDeclaration(node) && node.name) {
                const name = node.name.getText(sourceFile);
                const pos = sourceFile.getLineAndCharacterOfPosition(node.pos);
                symbolInfo = { name, kind: 'class', file: relativePath, line: pos.line + 1 };
            }

            if (symbolInfo) {
                allSymbols.push(symbolInfo);
            }

            ts.forEachChild(node, visit);
        }

        visit(sourceFile);
    }

    // Sort by kind priority, then name
    const kindOrder = { 'function': 0, 'class': 1, 'interface': 2, 'type': 3, 'const': 4 };
    allSymbols.sort((a, b) => {
        const orderA = kindOrder[a.kind] ?? 99;
        const orderB = kindOrder[b.kind] ?? 99;
        if (orderA !== orderB) return orderA - orderB;
        return a.name.localeCompare(b.name);
    });

    // Limit to topN
    const result = topN > 0 ? allSymbols.slice(0, topN) : allSymbols;

    console.log(JSON.stringify({
        path: projectPath,
        total: allSymbols.length,
        symbols: result
    }));
}

/**
 * Command: refs - Find all references to symbol at position.
 */
function outputReferences(filePath, line, column) {
    const projectPath = path.dirname(filePath);
    const configPath = ts.findConfigFile(projectPath, ts.sys.fileExists, 'tsconfig.json');

    if (!configPath) {
        console.log(JSON.stringify({ error: 'tsconfig.json not found', references: [] }));
        return;
    }

    // Create language service for find references
    const configFile = ts.readConfigFile(configPath, ts.sys.readFile);
    const parsed = ts.parseJsonConfigFileContent(
        configFile.config,
        ts.sys,
        path.dirname(configPath)
    );

    const files = {};
    for (const fileName of parsed.fileNames) {
        try {
            files[fileName] = {
                version: 0,
                text: fs.readFileSync(fileName, 'utf-8')
            };
        } catch (e) {
            // Skip files that can't be read (may be deleted or permissions issue)
            continue;
        }
    }

    const servicesHost = {
        getScriptFileNames: () => parsed.fileNames,
        getScriptVersion: (fileName) => files[fileName]?.version.toString() || '0',
        getScriptSnapshot: (fileName) => {
            if (!files[fileName]) {
                try {
                    const text = fs.readFileSync(fileName, 'utf-8');
                    files[fileName] = { version: 0, text };
                } catch (e) {
                    // File doesn't exist or can't be read
                    return undefined;
                }
            }
            return ts.ScriptSnapshot.fromString(files[fileName].text);
        },
        getCurrentDirectory: () => path.dirname(configPath),
        getCompilationSettings: () => parsed.options,
        getDefaultLibFileName: (options) => ts.getDefaultLibFilePath(options),
        fileExists: ts.sys.fileExists,
        readFile: ts.sys.readFile,
        readDirectory: ts.sys.readDirectory,
        directoryExists: ts.sys.directoryExists,
        getDirectories: ts.sys.getDirectories,
    };

    const services = ts.createLanguageService(servicesHost, ts.createDocumentRegistry());

    // Convert line/column to position
    const absolutePath = path.resolve(filePath);
    const sourceFile = services.getProgram()?.getSourceFile(absolutePath);

    if (!sourceFile) {
        console.log(JSON.stringify({ error: 'File not found', references: [] }));
        return;
    }

    const position = sourceFile.getPositionOfLineAndCharacter(line - 1, column);

    // Find references
    const refs = services.findReferences(absolutePath, position);
    const references = [];

    if (refs) {
        for (const refGroup of refs) {
            for (const ref of refGroup.references) {
                const refFile = services.getProgram()?.getSourceFile(ref.fileName);
                if (refFile) {
                    const startPos = refFile.getLineAndCharacterOfPosition(ref.textSpan.start);
                    const lineText = refFile.text.split('\n')[startPos.line]?.trim() || '';

                    references.push({
                        file: path.relative(projectPath, ref.fileName),
                        line: startPos.line + 1,
                        column: startPos.character,
                        context: lineText,
                        isDefinition: ref.isDefinition || false
                    });
                }
            }
        }
    }

    console.log(JSON.stringify({
        file: filePath,
        line,
        column,
        references
    }));
}

// Route to appropriate command
switch (query.command) {
    case 'sig':
        outputSignatures(query.file);
        break;
    case 'map':
        outputSymbolMap(query.path || '.', query.top || 10);
        break;
    case 'refs':
        outputReferences(query.file, query.line, query.column);
        break;
    default:
        console.error(JSON.stringify({
            error: `Unknown command: ${query.command}`,
            usage: {
                sig: { file: 'path/to/file.ts' },
                map: { path: '.', top: 10 },
                refs: { file: 'path/to/file.ts', line: 10, column: 5 }
            }
        }));
        process.exit(1);
}

process.exit(0);
