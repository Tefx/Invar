/**
 * @invar/ts-analyzer - TypeScript contract analysis using Compiler API
 *
 * Provides deep analysis of TypeScript code including:
 * - Cross-file type tracing
 * - z.infer<T> resolution
 * - Contract quality assessment
 * - Blind spot detection (unvalidated critical code)
 */

import * as ts from 'typescript';
import { dirname, resolve } from 'node:path';
import { z } from 'zod';

// ============================================================================
// Schemas
// ============================================================================

export const ContractQualitySchema = z.enum(['strong', 'medium', 'weak', 'useless']);
export type ContractQuality = z.infer<typeof ContractQualitySchema>;

export const ParamContractSchema = z.object({
  name: z.string(),
  type: z.string(),
  hasContract: z.boolean(),
  contractSource: z.object({
    schema: z.string().optional(),
    file: z.string().optional(),
    line: z.number().optional(),
    traceChain: z.array(z.string()).optional(),
  }).optional(),
  quality: z.object({
    score: ContractQualitySchema,
    hasTypeConstraint: z.boolean(),
    hasValueConstraint: z.boolean(),
    hasBoundaryConstraint: z.boolean(),
  }).optional(),
});

export type ParamContract = z.infer<typeof ParamContractSchema>;

export const FunctionAnalysisSchema = z.object({
  name: z.string(),
  file: z.string(),
  line: z.number(),
  contractStatus: z.enum(['complete', 'partial', 'missing']),
  params: z.array(ParamContractSchema),
  returnType: z.string().optional(),
  hasRuntimeValidation: z.boolean(),
  validationLocations: z.array(z.object({
    method: z.string(),
    line: z.number(),
  })),
  jsdocExample: z.boolean(),
});

export type FunctionAnalysis = z.infer<typeof FunctionAnalysisSchema>;

export const BlindSpotSchema = z.object({
  function: z.string(),
  file: z.string(),
  line: z.number(),
  risk: z.enum(['critical', 'high', 'medium', 'low']),
  reason: z.string(),
  suggestedSchema: z.string().optional(),
});

export type BlindSpot = z.infer<typeof BlindSpotSchema>;

export const AnalysisResultSchema = z.object({
  files: z.number(),
  functions: z.array(FunctionAnalysisSchema),
  coverage: z.object({
    total: z.number(),
    withContracts: z.number(),
    percent: z.number(),
  }),
  quality: z.object({
    strong: z.number(),
    medium: z.number(),
    weak: z.number(),
    useless: z.number(),
  }),
  blindSpots: z.array(BlindSpotSchema),
  dependencies: z.record(z.array(z.string())).optional(),
});

export type AnalysisResult = z.infer<typeof AnalysisResultSchema>;

// LX-06 Phase 3: Impact Analysis
export const ImpactAnalysisSchema = z.object({
  file: z.string(),
  directDependents: z.array(z.string()),
  transitiveDependents: z.array(z.string()),
  impactLevel: z.enum(['low', 'medium', 'high', 'critical']),
});

export type ImpactAnalysis = z.infer<typeof ImpactAnalysisSchema>;

export const AnalyzerOptionsSchema = z.object({
  path: z.string().default('.'),
  includePrivate: z.boolean().default(false),
  verbose: z.boolean().default(false),
  buildDependencyGraph: z.boolean().default(false),
});

export type AnalyzerOptions = z.infer<typeof AnalyzerOptionsSchema>;

// ============================================================================
// TypeScript Program Creation
// ============================================================================

/**
 * Find tsconfig.json and create TypeScript program.
 */
function createProgram(projectPath: string): ts.Program | null {
  const tsconfigPath = ts.findConfigFile(projectPath, ts.sys.fileExists, 'tsconfig.json');
  if (!tsconfigPath) {
    return null;
  }

  const configFile = ts.readConfigFile(tsconfigPath, ts.sys.readFile);
  if (configFile.error) {
    return null;
  }

  const parsedConfig = ts.parseJsonConfigFileContent(
    configFile.config,
    ts.sys,
    dirname(tsconfigPath)
  );

  return ts.createProgram(parsedConfig.fileNames, parsedConfig.options);
}

// ============================================================================
// Contract Detection
// ============================================================================

/**
 * High-risk keywords that indicate critical code paths.
 */
const HIGH_RISK_KEYWORDS = [
  'payment', 'pay', 'charge', 'refund',
  'auth', 'login', 'password', 'token', 'secret',
  'user', 'admin', 'permission', 'role',
  'delete', 'remove', 'destroy',
  'transfer', 'send', 'withdraw', 'deposit',
  'execute', 'eval', 'run',
];

/**
 * Check if a name contains high-risk keywords.
 */
function isHighRiskName(name: string): boolean {
  const lower = name.toLowerCase();
  return HIGH_RISK_KEYWORDS.some(keyword => lower.includes(keyword));
}

/**
 * Detect Zod schema types in a type string.
 */
function detectZodType(typeString: string): boolean {
  return typeString.includes('z.') ||
         typeString.includes('ZodType') ||
         typeString.includes('z.infer');
}

/**
 * Assess contract quality based on type characteristics.
 */
function assessContractQuality(typeString: string, hasRuntimeCheck: boolean): ContractQuality {
  // Check for value constraints
  const hasValueConstraint =
    typeString.includes('.min(') ||
    typeString.includes('.max(') ||
    typeString.includes('.positive(') ||
    typeString.includes('.negative(') ||
    typeString.includes('.email(') ||
    typeString.includes('.url(') ||
    typeString.includes('.uuid(') ||
    typeString.includes('.regex(');

  // Check for boundary constraints
  const hasBoundaryConstraint =
    typeString.includes('.length(') ||
    typeString.includes('.minLength(') ||
    typeString.includes('.maxLength(');

  // Check for enum/literal constraints
  const hasEnumConstraint =
    typeString.includes('.enum(') ||
    typeString.includes('.literal(');

  if (hasValueConstraint && hasBoundaryConstraint && hasRuntimeCheck) {
    return 'strong';
  }

  if ((hasValueConstraint || hasBoundaryConstraint || hasEnumConstraint) && hasRuntimeCheck) {
    return 'medium';
  }

  if (detectZodType(typeString) && hasRuntimeCheck) {
    return 'weak';
  }

  return 'useless';
}

// ============================================================================
// AST Analysis
// ============================================================================

/**
 * Analyze a function declaration or arrow function.
 */
function analyzeFunction(
  node: ts.FunctionDeclaration | ts.ArrowFunction | ts.MethodDeclaration,
  sourceFile: ts.SourceFile,
  checker: ts.TypeChecker,
  includePrivate: boolean
): FunctionAnalysis | null {
  // Get function name
  let name: string;
  if (ts.isFunctionDeclaration(node) || ts.isMethodDeclaration(node)) {
    if (!node.name) return null;
    name = node.name.getText(sourceFile);
  } else {
    // Arrow function - try to get from parent variable declaration
    const parent = node.parent;
    if (ts.isVariableDeclaration(parent) && ts.isIdentifier(parent.name)) {
      name = parent.name.getText(sourceFile);
    } else {
      return null; // Anonymous arrow function
    }
  }

  // Skip private functions unless requested
  if (!includePrivate && name.startsWith('_')) {
    return null;
  }

  const { line } = sourceFile.getLineAndCharacterOfPosition(node.getStart());
  const params: ParamContract[] = [];
  const validationLocations: { method: string; line: number }[] = [];
  let hasRuntimeValidation = false;

  // IMPORTANT: Check function body for .parse() calls FIRST
  // so hasRuntimeValidation is known before assessing param quality
  if (node.body) {
    const checkValidation = (n: ts.Node): void => {
      if (ts.isCallExpression(n)) {
        const expr = n.expression;
        if (ts.isPropertyAccessExpression(expr)) {
          const method = expr.name.getText(sourceFile);
          if (method === 'parse' || method === 'safeParse') {
            hasRuntimeValidation = true;
            const { line: validLine } = sourceFile.getLineAndCharacterOfPosition(n.getStart());
            validationLocations.push({ method, line: validLine + 1 });
          }
        }
      }
      ts.forEachChild(n, checkValidation);
    };
    checkValidation(node.body);
  }

  // Analyze parameters (now hasRuntimeValidation is known)
  for (const param of node.parameters) {
    const paramName = param.name.getText(sourceFile);
    const paramType = checker.typeToString(checker.getTypeAtLocation(param));

    const hasContract = detectZodType(paramType);
    const quality = hasContract
      ? {
          score: assessContractQuality(paramType, hasRuntimeValidation),
          hasTypeConstraint: true,
          hasValueConstraint: paramType.includes('.min(') || paramType.includes('.max('),
          hasBoundaryConstraint: paramType.includes('.length('),
        }
      : undefined;

    params.push({
      name: paramName,
      type: paramType,
      hasContract,
      quality,
    });
  }

  // Check for JSDoc @example
  const jsdoc = ts.getJSDocTags(node);
  const hasExample = jsdoc.some(tag => tag.tagName.getText() === 'example');

  // Determine contract status
  const hasAnyContract = params.some(p => p.hasContract);
  const allHaveContracts = params.length > 0 && params.every(p => p.hasContract);

  let contractStatus: 'complete' | 'partial' | 'missing';
  if (allHaveContracts && hasRuntimeValidation) {
    contractStatus = 'complete';
  } else if (hasAnyContract || hasRuntimeValidation) {
    contractStatus = 'partial';
  } else {
    contractStatus = 'missing';
  }

  // Get return type
  const signature = checker.getSignatureFromDeclaration(node);
  const returnType = signature
    ? checker.typeToString(checker.getReturnTypeOfSignature(signature))
    : undefined;

  return {
    name,
    file: sourceFile.fileName,
    line: line + 1,
    contractStatus,
    params,
    returnType,
    hasRuntimeValidation,
    validationLocations,
    jsdocExample: hasExample,
  };
}

/**
 * Detect blind spots (high-risk code without validation).
 */
function detectBlindSpots(functions: FunctionAnalysis[]): BlindSpot[] {
  const blindSpots: BlindSpot[] = [];

  for (const func of functions) {
    if (func.contractStatus === 'missing' && isHighRiskName(func.name)) {
      const risk = func.name.toLowerCase().includes('payment') ||
                   func.name.toLowerCase().includes('auth')
        ? 'critical'
        : 'high';

      blindSpots.push({
        function: func.name,
        file: func.file,
        line: func.line,
        risk,
        reason: `${risk === 'critical' ? 'Critical' : 'High-risk'} function without validation`,
        suggestedSchema: generateSuggestedSchema(func),
      });
    }
  }

  return blindSpots;
}

/**
 * Generate a suggested Zod schema for a function.
 */
function generateSuggestedSchema(func: FunctionAnalysis): string {
  if (func.params.length === 0) return 'z.void()';

  const fields = func.params.map(p => {
    const base = p.type.includes('string') ? 'z.string()'
      : p.type.includes('number') ? 'z.number()'
      : p.type.includes('boolean') ? 'z.boolean()'
      : 'z.unknown()';
    return `${p.name}: ${base}`;
  });

  return `z.object({ ${fields.join(', ')} })`;
}

// ============================================================================
// LX-06 Phase 3: Impact Analysis
// ============================================================================

/**
 * Build a dependency graph from TypeScript program.
 * Maps each file to the files it imports.
 */
function buildDependencyGraph(program: ts.Program): Record<string, string[]> {
  const graph: Record<string, string[]> = {};

  for (const sourceFile of program.getSourceFiles()) {
    if (sourceFile.isDeclarationFile) continue;
    if (sourceFile.fileName.includes('node_modules')) continue;

    const imports: string[] = [];

    const visit = (node: ts.Node): void => {
      // Handle import declarations: import { x } from './file'
      if (ts.isImportDeclaration(node)) {
        const moduleSpecifier = node.moduleSpecifier;
        if (ts.isStringLiteral(moduleSpecifier)) {
          const importPath = moduleSpecifier.text;
          // Only track relative imports (project files)
          if (importPath.startsWith('.')) {
            // Resolve to absolute path
            const resolvedPath = resolveImportPath(sourceFile.fileName, importPath, program);
            if (resolvedPath) {
              imports.push(resolvedPath);
            }
          }
        }
      }
      // Handle dynamic imports: import('./file')
      if (ts.isCallExpression(node) && node.expression.kind === ts.SyntaxKind.ImportKeyword) {
        const arg = node.arguments[0];
        if (arg && ts.isStringLiteral(arg)) {
          const importPath = arg.text;
          if (importPath.startsWith('.')) {
            const resolvedPath = resolveImportPath(sourceFile.fileName, importPath, program);
            if (resolvedPath) {
              imports.push(resolvedPath);
            }
          }
        }
      }
      ts.forEachChild(node, visit);
    };

    visit(sourceFile);
    graph[sourceFile.fileName] = [...new Set(imports)]; // Dedupe
  }

  return graph;
}

/**
 * Resolve an import path relative to the importing file.
 */
function resolveImportPath(fromFile: string, importPath: string, program: ts.Program): string | null {
  const compilerOptions = program.getCompilerOptions();
  const result = ts.resolveModuleName(importPath, fromFile, compilerOptions, ts.sys);

  if (result.resolvedModule) {
    return result.resolvedModule.resolvedFileName;
  }

  // Fallback: manual resolution for common cases
  const fromDir = dirname(fromFile);
  const extensions = ['.ts', '.tsx', '.js', '.jsx', ''];

  for (const ext of extensions) {
    const candidate = resolve(fromDir, importPath + ext);
    if (program.getSourceFile(candidate)) {
      return candidate;
    }
    // Try index file
    const indexCandidate = resolve(fromDir, importPath, 'index' + ext);
    if (program.getSourceFile(indexCandidate)) {
      return indexCandidate;
    }
  }

  return null;
}

/**
 * Get files that depend on a given file (reverse dependency lookup).
 */
function getDependents(
  file: string,
  graph: Record<string, string[]>,
  transitive: boolean = false
): string[] {
  const dependents: Set<string> = new Set();
  const visited: Set<string> = new Set();

  const findDependents = (target: string): void => {
    if (visited.has(target)) return;
    visited.add(target);

    for (const [sourceFile, imports] of Object.entries(graph)) {
      if (imports.includes(target)) {
        dependents.add(sourceFile);
        if (transitive) {
          findDependents(sourceFile);
        }
      }
    }
  };

  findDependents(file);
  return [...dependents];
}

/**
 * Analyze the impact of changing a specific file.
 *
 * @param file - The file being changed
 * @param graph - Dependency graph from buildDependencyGraph
 * @returns Impact analysis with dependents and severity
 */
export function analyzeImpact(file: string, graph: Record<string, string[]>): ImpactAnalysis {
  const directDependents = getDependents(file, graph, false);
  const transitiveDependents = getDependents(file, graph, true);

  // Calculate impact level based on dependent count
  let impactLevel: 'low' | 'medium' | 'high' | 'critical';
  const total = transitiveDependents.length;

  if (total === 0) {
    impactLevel = 'low';
  } else if (total <= 3) {
    impactLevel = 'medium';
  } else if (total <= 10) {
    impactLevel = 'high';
  } else {
    impactLevel = 'critical';
  }

  return {
    file,
    directDependents,
    transitiveDependents,
    impactLevel,
  };
}

// ============================================================================
// Main API
// ============================================================================

/**
 * Analyze a TypeScript project for contract coverage.
 *
 * @param options - Analysis options
 * @returns Analysis result with function contracts and blind spots
 *
 * @example
 * ```typescript
 * import { analyze } from '@invar/ts-analyzer';
 *
 * const result = await analyze({ path: './my-project' });
 * console.log(`Coverage: ${result.coverage.percent}%`);
 * console.log(`Blind spots: ${result.blindSpots.length}`);
 * ```
 */
export function analyze(options: Partial<AnalyzerOptions> = {}): AnalysisResult {
  const opts = AnalyzerOptionsSchema.parse(options);
  const projectPath = resolve(opts.path);

  const program = createProgram(projectPath);
  if (!program) {
    return {
      files: 0,
      functions: [],
      coverage: { total: 0, withContracts: 0, percent: 0 },
      quality: { strong: 0, medium: 0, weak: 0, useless: 0 },
      blindSpots: [],
    };
  }

  const checker = program.getTypeChecker();
  const functions: FunctionAnalysis[] = [];
  let fileCount = 0;

  for (const sourceFile of program.getSourceFiles()) {
    // Skip declaration files and node_modules
    if (sourceFile.isDeclarationFile) continue;
    if (sourceFile.fileName.includes('node_modules')) continue;

    fileCount++;

    const visit = (node: ts.Node): void => {
      if (
        ts.isFunctionDeclaration(node) ||
        ts.isArrowFunction(node) ||
        ts.isMethodDeclaration(node)
      ) {
        const analysis = analyzeFunction(node, sourceFile, checker, opts.includePrivate);
        if (analysis) {
          functions.push(analysis);
        }
      }
      ts.forEachChild(node, visit);
    };

    visit(sourceFile);
  }

  // Calculate metrics
  const withContracts = functions.filter(f => f.contractStatus !== 'missing').length;
  const percent = functions.length > 0 ? Math.round((withContracts / functions.length) * 100) : 0;

  const quality = {
    strong: 0,
    medium: 0,
    weak: 0,
    useless: 0,
  };

  for (const func of functions) {
    for (const param of func.params) {
      if (param.quality) {
        quality[param.quality.score]++;
      }
    }
  }

  const blindSpots = detectBlindSpots(functions);

  // LX-06 Phase 3: Build dependency graph if requested
  const dependencies = opts.buildDependencyGraph
    ? buildDependencyGraph(program)
    : undefined;

  return {
    files: fileCount,
    functions,
    coverage: {
      total: functions.length,
      withContracts,
      percent,
    },
    quality,
    blindSpots,
    dependencies,
  };
}

export { buildDependencyGraph };
export default analyze;
