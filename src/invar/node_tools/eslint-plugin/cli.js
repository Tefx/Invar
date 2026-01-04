#!/usr/bin/env node
"use strict";

// dist/cli.js
var import_eslint = require("eslint");
var import_path = require("path");
var import_url = require("url");

// dist/rules/require-schema-validation.js
var ZOD_TYPE_PATTERNS = [
  /^z\./,
  /ZodType/,
  /z\.infer/,
  /Schema$/
];
var RISK_KEYWORDS = [
  "payment",
  "pay",
  "auth",
  "authenticate",
  "login",
  "token",
  "validate",
  "verify",
  "encrypt",
  "decrypt",
  "password",
  "credential",
  "secret"
];
function isHighRiskFunction(functionName, filePath) {
  const combined = `${functionName} ${filePath}`.toLowerCase();
  return RISK_KEYWORDS.some((keyword) => combined.includes(keyword));
}
function matchesEnforcePattern(filePath, patterns) {
  if (patterns.length === 0)
    return false;
  const normalizedPath = filePath.replace(/\\/g, "/").toLowerCase();
  for (const pattern of patterns) {
    if (pattern.length > 200) {
      continue;
    }
    const normalizedPattern = pattern.replace(/\\/g, "/").toLowerCase();
    const escaped = normalizedPattern.replace(/[.+^${}()|[\]]/g, "\\$&");
    const regexPattern = escaped.replace(/\\\*\\\*/g, ".*?").replace(/\\\*/g, "[^/]*?").replace(/\\\?/g, ".");
    try {
      const regex = new RegExp(`^${regexPattern}$`);
      if (regex.test(normalizedPath)) {
        return true;
      }
    } catch (e) {
      continue;
    }
  }
  return false;
}
function isZodType(typeAnnotation) {
  return ZOD_TYPE_PATTERNS.some((pattern) => pattern.test(typeAnnotation));
}
function hasParseCall(body, paramName) {
  if (!body)
    return false;
  let found = false;
  const visit = (node) => {
    if (found)
      return;
    if (node.type === "CallExpression") {
      const callee = node.callee;
      if (callee.type === "MemberExpression") {
        const property = callee.property;
        if (property.type === "Identifier" && (property.name === "parse" || property.name === "safeParse")) {
          if (node.arguments.some((arg) => arg.type === "Identifier" && arg.name === paramName)) {
            found = true;
            return;
          }
        }
      }
    }
    for (const key of Object.keys(node)) {
      const value = node[key];
      if (value && typeof value === "object") {
        if (Array.isArray(value)) {
          for (const item of value) {
            if (item && typeof item === "object" && "type" in item) {
              visit(item);
            }
          }
        } else if ("type" in value) {
          visit(value);
        }
      }
    }
  };
  visit(body);
  return found;
}
var requireSchemaValidation = {
  meta: {
    type: "problem",
    docs: {
      description: "Require .parse() call for Zod-typed parameters",
      recommended: true
    },
    hasSuggestions: true,
    schema: [
      {
        type: "object",
        properties: {
          mode: {
            type: "string",
            enum: ["recommended", "strict", "risk-based"],
            default: "recommended"
          },
          enforceFor: {
            type: "array",
            items: {
              type: "string"
            },
            default: []
          }
        },
        additionalProperties: false
      }
    ],
    messages: {
      missingValidation: 'Parameter "{{name}}" has Zod type but no .parse() or .safeParse() call',
      missingValidationRisk: 'High-risk function "{{functionName}}": Parameter "{{name}}" has Zod type but no .parse() or .safeParse() call',
      addParseCall: 'Add .parse() validation for "{{name}}"'
    }
  },
  create(context) {
    const sourceCode = context.sourceCode || context.getSourceCode();
    const options = context.options[0] || {};
    const mode = options.mode || "recommended";
    const enforceFor = options.enforceFor || [];
    const filename = context.filename || context.getFilename();
    function getTypeAnnotationText(param) {
      const typedParam = param;
      if (!typedParam.typeAnnotation)
        return null;
      const text = sourceCode.getText(typedParam.typeAnnotation);
      return text.replace(/^:\s*/, "");
    }
    function getFunctionName2(node) {
      if (node.type === "FunctionDeclaration" && node.id) {
        return node.id.name;
      }
      return "anonymous";
    }
    function shouldCheck(functionName) {
      if (mode === "strict") {
        return true;
      }
      if (mode === "risk-based") {
        if (isHighRiskFunction(functionName, filename)) {
          return true;
        }
        if (matchesEnforcePattern(filename, enforceFor)) {
          return true;
        }
        return false;
      }
      return true;
    }
    function checkFunction(node, params) {
      const functionName = getFunctionName2(node);
      if (!shouldCheck(functionName)) {
        return;
      }
      const body = "body" in node ? node.body : null;
      const isRiskFunction = isHighRiskFunction(functionName, filename);
      for (const param of params) {
        if (param.typeAnnotation && isZodType(param.typeAnnotation)) {
          if (!hasParseCall(body, param.name)) {
            const schemaMatch = param.typeAnnotation.match(/typeof\s+(\w+)/);
            const schemaName = schemaMatch ? schemaMatch[1] : "Schema";
            const validatedVarName = `validated${param.name.charAt(0).toUpperCase()}${param.name.slice(1)}`;
            context.report({
              node,
              messageId: isRiskFunction ? "missingValidationRisk" : "missingValidation",
              data: {
                name: param.name,
                functionName
              },
              suggest: [
                {
                  messageId: "addParseCall",
                  data: { name: param.name },
                  fix(fixer) {
                    if (!body || body.type !== "BlockStatement")
                      return null;
                    const blockBody = body;
                    if (!blockBody.body || blockBody.body.length === 0)
                      return null;
                    const firstStatement = blockBody.body[0];
                    const firstStatementStart = firstStatement.loc?.start.column ?? 2;
                    const indent = " ".repeat(firstStatementStart);
                    const parseCode = `const ${validatedVarName} = ${schemaName}.parse(${param.name});
${indent}`;
                    return fixer.insertTextBefore(firstStatement, parseCode);
                  }
                }
              ]
            });
          }
        }
      }
    }
    function extractParamInfo(param) {
      if (param.type === "Identifier") {
        return {
          name: param.name,
          typeAnnotation: getTypeAnnotationText(param)
        };
      }
      if (param.type === "ObjectPattern" || param.type === "ArrayPattern") {
        const patternName = param.type === "ObjectPattern" ? "{...}" : "[...]";
        return {
          name: patternName,
          typeAnnotation: getTypeAnnotationText(param)
        };
      }
      if (param.type === "RestElement") {
        const restParam = param;
        const name = restParam.argument?.name || "...rest";
        return {
          name,
          typeAnnotation: getTypeAnnotationText(param)
        };
      }
      if (param.type === "AssignmentPattern") {
        const assignParam = param;
        if (assignParam.left) {
          return extractParamInfo(assignParam.left);
        }
      }
      return null;
    }
    return {
      FunctionDeclaration(node) {
        const params = node.params.map((p) => extractParamInfo(p)).filter((p) => p !== null);
        checkFunction(node, params);
      },
      ArrowFunctionExpression(node) {
        const params = node.params.map((p) => extractParamInfo(p)).filter((p) => p !== null);
        checkFunction(node, params);
      }
    };
  }
};

// dist/rules/no-io-in-core.js
var IO_MODULES = /* @__PURE__ */ new Set([
  "fs",
  "fs/promises",
  "node:fs",
  "node:fs/promises",
  "path",
  "node:path",
  "http",
  "https",
  "node:http",
  "node:https",
  "net",
  "node:net",
  "child_process",
  "node:child_process",
  "readline",
  "node:readline",
  "process",
  "node:process"
]);
var IO_PACKAGE_PATTERNS = [
  /^axios/,
  /^node-fetch/,
  /^got$/,
  /^superagent/,
  /^request/,
  /^pg$/,
  /^mysql/,
  /^mongodb/,
  /^redis/,
  /^ioredis/,
  /^@aws-sdk\//,
  /^@vercel\//
];
function isIoModule(source) {
  if (IO_MODULES.has(source))
    return true;
  return IO_PACKAGE_PATTERNS.some((pattern) => pattern.test(source));
}
function isInCoreDirectory(filename) {
  const normalized = filename.replace(/\\/g, "/").toLowerCase();
  return normalized.includes("/core/");
}
var noIoInCore = {
  meta: {
    type: "problem",
    docs: {
      description: "Forbid I/O imports in /core/ directories",
      recommended: true
    },
    schema: [],
    messages: {
      ioInCore: 'I/O module "{{module}}" is not allowed in /core/ directory. Move I/O to /shell/ or inject as parameter.'
    }
  },
  create(context) {
    const filename = context.filename || context.getFilename();
    if (!isInCoreDirectory(filename)) {
      return {};
    }
    return {
      ImportDeclaration(node) {
        const source = node.source.value;
        if (typeof source === "string" && isIoModule(source)) {
          context.report({
            node,
            messageId: "ioInCore",
            data: { module: source }
          });
        }
      },
      CallExpression(node) {
        if (node.callee.type === "Identifier" && node.callee.name === "require" && node.arguments.length > 0 && node.arguments[0].type === "Literal") {
          const source = node.arguments[0].value;
          if (typeof source === "string" && isIoModule(source)) {
            context.report({
              node,
              messageId: "ioInCore",
              data: { module: source }
            });
          }
        }
      }
    };
  }
};

// dist/rules/shell-result-type.js
var RESULT_TYPE_PATTERNS = [
  /^Result</,
  /^ResultAsync</,
  /^Ok</,
  /^Err</,
  /^Either</,
  /^Left</,
  /^Right</
];
function isResultType(typeAnnotation) {
  return RESULT_TYPE_PATTERNS.some((pattern) => pattern.test(typeAnnotation));
}
function isInShellDirectory(filename) {
  return filename.includes("/shell/") || filename.includes("\\shell\\");
}
function isExported(node) {
  const parent = node.parent;
  if (!parent)
    return false;
  if (parent.type === "ExportNamedDeclaration")
    return true;
  if (parent.type === "ExportDefaultDeclaration")
    return true;
  if (parent.type === "VariableDeclarator") {
    const grandparent = parent.parent;
    if (grandparent?.type === "VariableDeclaration") {
      const greatGrandparent = grandparent.parent;
      if (greatGrandparent?.type === "ExportNamedDeclaration")
        return true;
    }
  }
  return false;
}
var shellResultType = {
  meta: {
    type: "suggestion",
    docs: {
      description: "Shell functions must return Result<T, E> type",
      recommended: true
    },
    hasSuggestions: true,
    schema: [
      {
        type: "object",
        properties: {
          checkPrivate: {
            type: "boolean",
            default: false
          }
        },
        additionalProperties: false
      }
    ],
    messages: {
      missingResultType: 'Shell function "{{name}}" should return Result<T, E> type for explicit error handling',
      wrapWithResult: "Wrap return type with Result<{{returnType}}, Error>"
    }
  },
  create(context) {
    const filename = context.filename || context.getFilename();
    const sourceCode = context.sourceCode || context.getSourceCode();
    const options = context.options[0] || {};
    const checkPrivate = options.checkPrivate || false;
    if (!isInShellDirectory(filename)) {
      return {};
    }
    function getReturnTypeText(node) {
      const typedNode = node;
      if (!typedNode.returnType)
        return null;
      const text = sourceCode.getText(typedNode.returnType);
      return text.replace(/^:\s*/, "");
    }
    function checkFunction(node, name, returnType) {
      if (!name)
        return;
      if (!checkPrivate && name.startsWith("_"))
        return;
      if (!isExported(node))
        return;
      if (!returnType || !isResultType(returnType)) {
        const suggestedReturnType = returnType || "void";
        const typedNode = node;
        context.report({
          node,
          messageId: "missingResultType",
          data: { name },
          suggest: typedNode.returnType ? [
            {
              messageId: "wrapWithResult",
              data: { returnType: suggestedReturnType },
              fix(fixer) {
                if (!typedNode.returnType)
                  return null;
                const newType = `Result<${suggestedReturnType}, Error>`;
                return fixer.replaceText(typedNode.returnType, `: ${newType}`);
              }
            }
          ] : []
        });
      }
    }
    return {
      FunctionDeclaration(node) {
        const name = node.id?.name || null;
        const returnType = getReturnTypeText(node);
        checkFunction(node, name, returnType);
      },
      ArrowFunctionExpression(node) {
        const parent = node.parent;
        const name = parent?.type === "VariableDeclarator" && parent.id?.name ? parent.id.name : null;
        const returnType = getReturnTypeText(node);
        checkFunction(node, name, returnType);
      }
    };
  }
};

// dist/rules/no-any-in-schema.js
var noAnyInSchema = {
  meta: {
    type: "problem",
    docs: {
      description: "Forbid z.any() in Zod schemas",
      recommended: true
    },
    schema: [],
    messages: {
      noAny: "Avoid z.any() - use a specific type or z.unknown() with refinement"
    }
  },
  create(context) {
    return {
      CallExpression(node) {
        const callee = node.callee;
        if (callee.type === "MemberExpression" && callee.object.type === "Identifier" && callee.object.name === "z" && callee.property.type === "Identifier" && callee.property.name === "any") {
          context.report({
            node,
            messageId: "noAny"
          });
        }
      }
    };
  }
};

// dist/rules/require-jsdoc-example.js
function isExported2(node) {
  const parent = node.parent;
  if (!parent)
    return false;
  if (parent.type === "ExportNamedDeclaration")
    return true;
  if (parent.type === "ExportDefaultDeclaration")
    return true;
  return false;
}
var requireJsdocExample = {
  meta: {
    type: "problem",
    docs: {
      description: "Exported functions must have @example in JSDoc",
      recommended: true
    },
    schema: [],
    messages: {
      missingExample: 'Exported function "{{name}}" must have @example in JSDoc (required for doctest)'
    }
  },
  create(context) {
    function checkFunction(node, name, skipExportCheck = false) {
      if (!name)
        return;
      if (!skipExportCheck && !isExported2(node))
        return;
      const sourceCode = context.sourceCode || context.getSourceCode();
      const comments = sourceCode.getCommentsBefore(node);
      const hasExample = comments.some((comment) => comment.type === "Block" && comment.value.includes("@example"));
      if (!hasExample) {
        context.report({
          node,
          messageId: "missingExample",
          data: { name }
        });
      }
    }
    return {
      FunctionDeclaration(node) {
        checkFunction(node, node.id?.name || null);
      },
      // Also check arrow functions assigned to exported variables
      // Selector guarantees this is already exported, so skipExportCheck=true
      "ExportNamedDeclaration > VariableDeclaration > VariableDeclarator > ArrowFunctionExpression"(node) {
        const anyNode = node;
        const name = anyNode.parent?.id?.name || null;
        if (!name)
          return;
        const sourceCode = context.sourceCode || context.getSourceCode();
        const exportDeclaration = anyNode.parent?.parent?.parent;
        const comments = exportDeclaration?.type === "ExportNamedDeclaration" ? sourceCode.getCommentsBefore(exportDeclaration) : sourceCode.getCommentsBefore(node);
        const hasExample = comments.some((comment) => comment.type === "Block" && comment.value.includes("@example"));
        if (!hasExample) {
          context.report({
            node,
            messageId: "missingExample",
            data: { name }
          });
        }
      }
    };
  }
};

// dist/utils/layer-detection.js
var LAYER_LIMITS = {
  core: {
    maxFileLines: 650,
    maxFunctionLines: 65
  },
  shell: {
    maxFileLines: 910,
    maxFunctionLines: 130
  },
  tests: {
    maxFileLines: 1300,
    maxFunctionLines: 260
  },
  default: {
    maxFileLines: 780,
    maxFunctionLines: 104
  }
};
function getLayer(filename) {
  const normalized = filename.replace(/\\/g, "/").toLowerCase();
  if (normalized.includes("/test/") || normalized.includes("/tests/") || normalized.includes("/__tests__/") || normalized.endsWith(".test.ts") || normalized.endsWith(".test.tsx") || normalized.endsWith(".test.js") || normalized.endsWith(".test.jsx") || normalized.endsWith(".spec.ts") || normalized.endsWith(".spec.tsx") || normalized.endsWith(".spec.js") || normalized.endsWith(".spec.jsx")) {
    return "tests";
  }
  if (normalized.includes("/core/") || normalized.endsWith("/core") || normalized.startsWith("core/")) {
    return "core";
  }
  if (normalized.includes("/shell/") || normalized.endsWith("/shell") || normalized.startsWith("shell/")) {
    return "shell";
  }
  return "default";
}
function getLimits(filename) {
  const layer = getLayer(filename);
  return LAYER_LIMITS[layer];
}

// dist/rules/max-file-lines.js
var maxFileLines = {
  meta: {
    type: "problem",
    docs: {
      description: "Enforce maximum file length with layer-based limits",
      recommended: true
    },
    schema: [
      {
        type: "object",
        properties: {
          max: {
            type: "number",
            minimum: 1
          },
          skipBlankLines: {
            type: "boolean"
          },
          skipComments: {
            type: "boolean"
          }
        },
        additionalProperties: false
      }
    ],
    messages: {
      tooManyLines: "File has {{actual}} lines ({{layer}} layer max: {{max}}). Consider splitting into smaller modules."
    }
  },
  create(context) {
    const filename = context.filename || context.getFilename();
    const layer = getLayer(filename);
    const limits = getLimits(filename);
    const options = context.options[0] || {};
    const maxLines = options.max !== void 0 ? options.max : limits.maxFileLines;
    const skipBlankLines = options.skipBlankLines || false;
    const skipComments = options.skipComments || false;
    return {
      Program(node) {
        const sourceCode = context.sourceCode || context.getSourceCode();
        const lines = sourceCode.lines;
        let actualLines = lines.length;
        if (skipBlankLines || skipComments) {
          const allComments = sourceCode.getAllComments();
          const commentLines = /* @__PURE__ */ new Set();
          if (skipComments) {
            allComments.forEach((comment) => {
              if (!comment.loc)
                return;
              const start = comment.loc.start.line;
              const end = comment.loc.end.line;
              for (let i = start; i <= end; i++) {
                commentLines.add(i);
              }
            });
          }
          actualLines = 0;
          for (let i = 0; i < lines.length; i++) {
            const lineNum = i + 1;
            const line = lines[i];
            if (!line)
              continue;
            if (skipComments && commentLines.has(lineNum)) {
              continue;
            }
            if (skipBlankLines && line.trim().length === 0) {
              continue;
            }
            actualLines++;
          }
        }
        if (actualLines > maxLines) {
          context.report({
            node,
            messageId: "tooManyLines",
            data: {
              actual: String(actualLines),
              max: String(maxLines),
              layer
            }
          });
        }
      }
    };
  }
};

// dist/rules/max-function-lines.js
function getFunctionName(node) {
  const anyNode = node;
  if (anyNode.id?.name) {
    return anyNode.id.name;
  }
  if (anyNode.key?.name) {
    return anyNode.key.name;
  }
  if (anyNode.parent?.type === "VariableDeclarator" && anyNode.parent.id?.name) {
    return anyNode.parent.id.name;
  }
  return "(anonymous)";
}
var maxFunctionLines = {
  meta: {
    type: "problem",
    docs: {
      description: "Enforce maximum function length with layer-based limits",
      recommended: true
    },
    schema: [
      {
        type: "object",
        properties: {
          max: {
            type: "number",
            minimum: 1
          },
          skipBlankLines: {
            type: "boolean"
          },
          skipComments: {
            type: "boolean"
          }
        },
        additionalProperties: false
      }
    ],
    messages: {
      tooManyLines: 'Function "{{name}}" has {{actual}} lines ({{layer}} layer max: {{max}}). Consider breaking into smaller functions.'
    }
  },
  create(context) {
    const filename = context.filename || context.getFilename();
    const layer = getLayer(filename);
    const limits = getLimits(filename);
    const options = context.options[0] || {};
    const maxLines = options.max !== void 0 ? options.max : limits.maxFunctionLines;
    const skipBlankLines = options.skipBlankLines || false;
    const skipComments = options.skipComments || false;
    function checkFunction(node) {
      const sourceCode = context.sourceCode || context.getSourceCode();
      const loc = node.loc;
      if (!loc)
        return;
      let actualLines = loc.end.line - loc.start.line + 1;
      if (skipBlankLines || skipComments) {
        const allComments = sourceCode.getAllComments();
        const commentLines = /* @__PURE__ */ new Set();
        if (skipComments) {
          allComments.forEach((comment) => {
            if (!comment.loc)
              return;
            const start = comment.loc.start.line;
            const end = comment.loc.end.line;
            for (let i = start; i <= end; i++) {
              commentLines.add(i);
            }
          });
        }
        actualLines = 0;
        for (let lineNum = loc.start.line; lineNum <= loc.end.line; lineNum++) {
          const line = sourceCode.lines[lineNum - 1];
          if (!line)
            continue;
          if (skipComments && commentLines.has(lineNum)) {
            continue;
          }
          if (skipBlankLines && line.trim().length === 0) {
            continue;
          }
          actualLines++;
        }
      }
      if (actualLines > maxLines) {
        const name = getFunctionName(node);
        context.report({
          node,
          messageId: "tooManyLines",
          data: {
            name,
            actual: String(actualLines),
            max: String(maxLines),
            layer
          }
        });
      }
    }
    return {
      FunctionDeclaration(node) {
        checkFunction(node);
      },
      FunctionExpression(node) {
        checkFunction(node);
      },
      ArrowFunctionExpression(node) {
        checkFunction(node);
      }
    };
  }
};

// dist/rules/no-empty-schema.js
var noEmptySchema = {
  meta: {
    type: "problem",
    docs: {
      description: "Forbid empty or permissive Zod schemas that defeat validation",
      recommended: true
    },
    schema: [],
    messages: {
      emptyObject: "Empty z.object({}) accepts any object. Add properties or use z.record()",
      passthrough: "Schema with .passthrough() bypasses unknown property validation. Remove or use .strict()",
      loose: "Schema with .loose() ignores unknown properties. Remove or use .strict()"
    }
  },
  create(context) {
    return {
      CallExpression(node) {
        const callee = node.callee;
        if (callee.type === "MemberExpression" && callee.object.type === "Identifier" && callee.object.name === "z" && callee.property.type === "Identifier" && callee.property.name === "object") {
          const args = node.arguments;
          if (args.length === 1 && args[0].type === "ObjectExpression") {
            const properties = args[0].properties;
            if (properties.length === 0) {
              context.report({
                node,
                messageId: "emptyObject"
              });
            }
          }
        }
        if (callee.type === "MemberExpression" && callee.property.type === "Identifier" && callee.property.name === "passthrough") {
          context.report({
            node,
            messageId: "passthrough"
          });
        }
        if (callee.type === "MemberExpression" && callee.property.type === "Identifier" && callee.property.name === "loose") {
          context.report({
            node,
            messageId: "loose"
          });
        }
      }
    };
  }
};

// dist/rules/no-redundant-type-schema.js
function hasRefinements(node, baseType) {
  const refinementMethods = {
    string: ["min", "max", "length", "email", "url", "emoji", "uuid", "cuid", "regex", "startsWith", "endsWith", "trim", "toLowerCase", "toUpperCase", "refine", "transform"],
    number: ["min", "max", "int", "positive", "negative", "nonnegative", "nonpositive", "multipleOf", "finite", "safe", "refine", "transform"],
    boolean: []
    // boolean is always redundant
  };
  const allowedMethods = refinementMethods[baseType] || [];
  let current = node.parent;
  while (current) {
    if (current.type === "CallExpression") {
      const callee = current.callee;
      if (callee.type === "MemberExpression" && callee.property.type === "Identifier") {
        const methodName = callee.property.name;
        if (allowedMethods.includes(methodName)) {
          return true;
        }
      }
      current = current.parent;
    } else if (current.type === "VariableDeclarator" || current.type === "Property") {
      break;
    } else {
      current = current.parent;
    }
  }
  return false;
}
var noRedundantTypeSchema = {
  meta: {
    type: "suggestion",
    docs: {
      description: "Forbid Zod schemas that only repeat TypeScript types without adding constraints",
      recommended: true
    },
    schema: [],
    messages: {
      redundantString: "z.string() without constraints is redundant. Add .min(), .max(), .regex(), or use plain TypeScript type.",
      redundantNumber: "z.number() without constraints is redundant. Add .min(), .max(), .int(), or use plain TypeScript type.",
      redundantBoolean: "z.boolean() is almost always redundant. Use plain TypeScript boolean type unless validating external input."
    }
  },
  create(context) {
    const sourceCode = context.sourceCode || context.getSourceCode();
    return {
      CallExpression(node) {
        const callee = node.callee;
        if (callee.type === "MemberExpression" && callee.object.type === "Identifier" && callee.object.name === "z" && callee.property.type === "Identifier") {
          const typeName = callee.property.name;
          if (!node.parent) {
            const parents = sourceCode.getAncestors(node);
            node.parent = parents[parents.length - 1];
          }
          if (typeName === "string" && !hasRefinements(node, "string")) {
            context.report({
              node,
              messageId: "redundantString"
            });
          }
          if (typeName === "number" && !hasRefinements(node, "number")) {
            context.report({
              node,
              messageId: "redundantNumber"
            });
          }
          if (typeName === "boolean") {
            context.report({
              node,
              messageId: "redundantBoolean"
            });
          }
        }
      }
    };
  }
};

// dist/rules/require-complete-validation.js
function isZodInferType(typeAnnotation) {
  if (!typeAnnotation || typeAnnotation.type !== "TSTypeReference") {
    return false;
  }
  const typeRef = typeAnnotation;
  if (typeRef.typeName.type === "TSQualifiedName" && typeRef.typeName.left.type === "Identifier" && typeRef.typeName.left.name === "z" && typeRef.typeName.right.type === "Identifier" && typeRef.typeName.right.name === "infer") {
    return true;
  }
  if (typeRef.typeParameters && typeRef.typeParameters.params.length > 0) {
    const firstParam = typeRef.typeParameters.params[0];
    if (firstParam.type === "TSTypeQuery") {
      return true;
    }
  }
  return false;
}
var requireCompleteValidation = {
  meta: {
    type: "suggestion",
    docs: {
      description: "Require all function parameters to be validated, or none",
      recommended: true
    },
    schema: [],
    messages: {
      partialValidation: "Function has {{validated}} parameter(s) with Zod schema validation but {{unvalidated}} without. Either validate all parameters or use plain TypeScript types for all."
    }
  },
  create(context) {
    function checkFunction(node) {
      const params = node.params;
      if (params.length === 0) {
        return;
      }
      let validatedCount = 0;
      let unvalidatedCount = 0;
      for (const param of params) {
        if (param.type === "Identifier" && param.typeAnnotation) {
          const typeAnnotation = param.typeAnnotation.typeAnnotation;
          if (isZodInferType(typeAnnotation)) {
            validatedCount++;
          } else {
            unvalidatedCount++;
          }
        } else if (param.type === "AssignmentPattern") {
          if (param.left.type === "Identifier" && param.left.typeAnnotation) {
            const typeAnnotation = param.left.typeAnnotation.typeAnnotation;
            if (isZodInferType(typeAnnotation)) {
              validatedCount++;
            } else {
              unvalidatedCount++;
            }
          }
        } else {
          unvalidatedCount++;
        }
      }
      if (validatedCount > 0 && unvalidatedCount > 0) {
        context.report({
          node,
          messageId: "partialValidation",
          data: {
            validated: String(validatedCount),
            unvalidated: String(unvalidatedCount)
          }
        });
      }
    }
    return {
      FunctionDeclaration: checkFunction,
      FunctionExpression: checkFunction,
      ArrowFunctionExpression: checkFunction
    };
  }
};

// dist/rules/no-runtime-imports.js
var noRuntimeImports = {
  meta: {
    type: "problem",
    docs: {
      description: "Forbid imports inside functions (require runtime imports at module top-level)",
      recommended: true
    },
    schema: [],
    messages: {
      runtimeRequire: "Runtime require() detected. Move imports to module top-level for predictability.",
      runtimeImport: "Dynamic import() detected. Move imports to module top-level for predictability."
    }
  },
  create(context) {
    function isInsideFunction(node) {
      const ancestors = context.sourceCode?.getAncestors?.(node) || context.getAncestors();
      for (const ancestor of ancestors) {
        if (ancestor.type === "FunctionDeclaration" || ancestor.type === "FunctionExpression" || ancestor.type === "ArrowFunctionExpression") {
          return true;
        }
      }
      return false;
    }
    return {
      CallExpression(node) {
        const callNode = node;
        if (callNode.callee.type === "Identifier" && callNode.callee.name === "require") {
          if (isInsideFunction(node)) {
            context.report({
              node,
              messageId: "runtimeRequire"
            });
          }
        }
      },
      ImportExpression(node) {
        if (isInsideFunction(node)) {
          context.report({
            node,
            messageId: "runtimeImport"
          });
        }
      }
    };
  }
};

// dist/rules/no-impure-calls-in-core.js
var noImpureCallsInCore = {
  meta: {
    type: "problem",
    docs: {
      description: "Forbid Core functions calling Shell functions (imports from shell/)",
      recommended: true
    },
    schema: [],
    messages: {
      shellImportInCore: 'Core file importing from Shell: "{{source}}". Core must be pure - move I/O logic to Shell or extract pure logic.'
    }
  },
  create(context) {
    const filename = context.filename || context.getFilename();
    const isCore = /[/\\]core[/\\]/.test(filename);
    if (!isCore) {
      return {};
    }
    return {
      ImportDeclaration(node) {
        const importNode = node;
        if (importNode.source && importNode.source.type === "Literal") {
          const source = String(importNode.source.value);
          if (/[/\\]shell[/\\]/.test(source) || /^shell[/\\]/.test(source)) {
            context.report({
              node,
              messageId: "shellImportInCore",
              data: {
                source
              }
            });
          }
        }
      }
    };
  }
};

// dist/rules/no-pure-logic-in-shell.js
var IO_IDENTIFIERS = [
  "fs",
  "readFile",
  "writeFile",
  "fetch",
  "axios",
  "http",
  "https",
  "db",
  "database",
  "query",
  "execute",
  "readFileSync",
  "writeFileSync",
  "existsSync",
  "mkdir",
  "rmdir",
  "unlink",
  "Result",
  "Success",
  "Failure",
  "readdir",
  "stat",
  "access",
  "net",
  "spawn",
  "exec",
  "execSync",
  "child_process",
  "WebSocket",
  "XMLHttpRequest",
  "request",
  "got",
  "console"
];
var noPureLogicInShell = {
  meta: {
    type: "suggestion",
    docs: {
      description: "Warn when Shell functions contain pure logic that should be in Core",
      recommended: false
    },
    schema: [],
    messages: {
      pureLogicInShell: 'Shell function "{{name}}" appears to contain pure logic. Consider moving to Core if it performs no I/O.'
    }
  },
  create(context) {
    const filename = context.filename || context.getFilename();
    const isShell = /[/\\]shell[/\\]/.test(filename);
    if (!isShell) {
      return {};
    }
    function hasIOIndicators(node) {
      let hasIO = false;
      if (node.async) {
        hasIO = true;
      }
      function visit(n) {
        if (hasIO)
          return;
        if (n.type === "Identifier") {
          if (IO_IDENTIFIERS.includes(n.name)) {
            hasIO = true;
            return;
          }
        }
        for (const key of Object.keys(n)) {
          const value = n[key];
          if (value && typeof value === "object") {
            if (Array.isArray(value)) {
              for (const item of value) {
                if (item && typeof item === "object" && "type" in item) {
                  visit(item);
                }
              }
            } else if ("type" in value) {
              visit(value);
            }
          }
        }
      }
      if (node.body) {
        visit(node.body);
      }
      return hasIO;
    }
    function hasSubstantialLogic(node) {
      if (!node.body || node.body.type !== "BlockStatement") {
        return false;
      }
      const blockBody = node.body;
      return blockBody.body.length > 3;
    }
    function getFunctionName2(node) {
      if (node.type === "FunctionDeclaration" && node.id) {
        return node.id.name;
      }
      if (node.type === "FunctionExpression" && node.id) {
        return node.id.name;
      }
      try {
        const ancestors = context.getAncestors();
        for (let i = ancestors.length - 1; i >= 0; i--) {
          const ancestor = ancestors[i];
          if (ancestor.type === "VariableDeclarator") {
            const varDecl = ancestor;
            if (varDecl.id && varDecl.id.type === "Identifier" && varDecl.id.name) {
              return varDecl.id.name;
            }
          }
        }
      } catch {
      }
      return "anonymous";
    }
    function checkFunction(node) {
      const functionName = getFunctionName2(node);
      if (functionName === "anonymous" || functionName.length < 3) {
        return;
      }
      if (hasIOIndicators(node)) {
        return;
      }
      if (hasSubstantialLogic(node)) {
        context.report({
          node,
          messageId: "pureLogicInShell",
          data: {
            name: functionName
          }
        });
      }
    }
    return {
      FunctionDeclaration: checkFunction,
      FunctionExpression: checkFunction,
      ArrowFunctionExpression: checkFunction
    };
  }
};

// dist/rules/shell-complexity.js
var DEFAULT_MAX_STATEMENTS = 20;
var DEFAULT_MAX_COMPLEXITY = 10;
var shellComplexity = {
  meta: {
    type: "suggestion",
    docs: {
      description: "Warn when Shell functions are too complex (should extract logic to Core)",
      recommended: false
    },
    schema: [
      {
        type: "object",
        properties: {
          maxStatements: {
            type: "number",
            default: DEFAULT_MAX_STATEMENTS
          },
          maxComplexity: {
            type: "number",
            default: DEFAULT_MAX_COMPLEXITY
          }
        },
        additionalProperties: false
      }
    ],
    messages: {
      tooManyStatements: 'Shell function "{{name}}" has {{count}} statements (max {{max}}). Consider extracting pure logic to Core.',
      tooComplex: 'Shell function "{{name}}" has complexity {{complexity}} (max {{max}}). Consider splitting into smaller functions.'
    }
  },
  create(context) {
    const filename = context.filename || context.getFilename();
    const isShell = /[/\\]shell[/\\]/.test(filename);
    if (!isShell) {
      return {};
    }
    const options = context.options[0] || {};
    const maxStatements = options.maxStatements || DEFAULT_MAX_STATEMENTS;
    const maxComplexity = options.maxComplexity || DEFAULT_MAX_COMPLEXITY;
    function countStatements(node) {
      if (!node.body || node.body.type !== "BlockStatement") {
        return 0;
      }
      let count = 0;
      function visit(n) {
        if (n.type === "ExpressionStatement" || n.type === "VariableDeclaration" || n.type === "ReturnStatement" || n.type === "IfStatement" || n.type === "ForStatement" || n.type === "WhileStatement" || n.type === "DoWhileStatement" || n.type === "SwitchStatement" || n.type === "TryStatement" || n.type === "ThrowStatement") {
          count++;
        }
        for (const key of Object.keys(n)) {
          const value = n[key];
          if (value && typeof value === "object") {
            if (Array.isArray(value)) {
              for (const item of value) {
                if (item && typeof item === "object" && "type" in item) {
                  visit(item);
                }
              }
            } else if ("type" in value) {
              visit(value);
            }
          }
        }
      }
      visit(node.body);
      return count;
    }
    function calculateComplexity(node) {
      if (!node.body) {
        return 1;
      }
      let complexity = 1;
      function visit(n) {
        if (n.type === "IfStatement" || n.type === "ForStatement" || n.type === "ForInStatement" || n.type === "ForOfStatement" || n.type === "WhileStatement" || n.type === "DoWhileStatement" || n.type === "ConditionalExpression" || // ternary ? :
        n.type === "CatchClause") {
          complexity++;
        }
        if (n.type === "SwitchCase") {
          const caseNode = n;
          if (caseNode.test !== null) {
            complexity++;
          }
        }
        if (n.type === "LogicalExpression") {
          const logicalNode = n;
          if (logicalNode.operator === "&&" || logicalNode.operator === "||" || logicalNode.operator === "??") {
            complexity++;
          }
        }
        for (const key of Object.keys(n)) {
          const value = n[key];
          if (value && typeof value === "object") {
            if (Array.isArray(value)) {
              for (const item of value) {
                if (item && typeof item === "object" && "type" in item) {
                  visit(item);
                }
              }
            } else if ("type" in value) {
              visit(value);
            }
          }
        }
      }
      visit(node.body);
      return complexity;
    }
    function getFunctionName2(node) {
      if (node.type === "FunctionDeclaration" && node.id) {
        return node.id.name;
      }
      if (node.type === "FunctionExpression" && node.id) {
        return node.id.name;
      }
      try {
        const ancestors = context.getAncestors();
        for (let i = ancestors.length - 1; i >= 0; i--) {
          const ancestor = ancestors[i];
          if (ancestor.type === "VariableDeclarator") {
            const varDecl = ancestor;
            if (varDecl.id && varDecl.id.type === "Identifier" && varDecl.id.name) {
              return varDecl.id.name;
            }
          }
        }
      } catch {
      }
      return "anonymous";
    }
    function checkFunction(node) {
      const functionName = getFunctionName2(node);
      if (functionName === "anonymous" || functionName.length < 3) {
        return;
      }
      const statementCount = countStatements(node);
      if (statementCount > maxStatements) {
        context.report({
          node,
          messageId: "tooManyStatements",
          data: {
            name: functionName,
            count: String(statementCount),
            max: String(maxStatements)
          }
        });
      }
      const complexity = calculateComplexity(node);
      if (complexity > maxComplexity) {
        context.report({
          node,
          messageId: "tooComplex",
          data: {
            name: functionName,
            complexity: String(complexity),
            max: String(maxComplexity)
          }
        });
      }
    }
    return {
      FunctionDeclaration: checkFunction,
      FunctionExpression: checkFunction,
      ArrowFunctionExpression: checkFunction
    };
  }
};

// dist/rules/thin-entry-points.js
var ENTRY_POINT_PATTERNS = [
  /index\.(ts|js|tsx|jsx)$/,
  /main\.(ts|js|tsx|jsx)$/,
  /cli\.(ts|js|tsx|jsx)$/,
  /app\.(ts|js|tsx|jsx)$/,
  /server\.(ts|js|tsx|jsx)$/
];
var DEFAULT_MAX_STATEMENTS2 = 10;
var thinEntryPoints = {
  meta: {
    type: "suggestion",
    docs: {
      description: "Warn when entry point files contain substantial logic (should delegate to Core/Shell)",
      recommended: false
    },
    schema: [
      {
        type: "object",
        properties: {
          maxStatements: {
            type: "number",
            default: DEFAULT_MAX_STATEMENTS2
          }
        },
        additionalProperties: false
      }
    ],
    messages: {
      tooMuchLogic: 'Entry point file "{{filename}}" has {{count}} non-import statements (max {{max}}). Entry points should be thin - delegate to Core/Shell.',
      hasComplexLogic: 'Entry point file "{{filename}}" contains {{type}}. Entry points should only import/export, not implement logic.'
    }
  },
  create(context) {
    const filename = context.filename || context.getFilename();
    const isEntryPoint = ENTRY_POINT_PATTERNS.some((pattern) => pattern.test(filename));
    if (!isEntryPoint) {
      return {};
    }
    const options = context.options[0] || {};
    const maxStatements = options.maxStatements || DEFAULT_MAX_STATEMENTS2;
    function isImportOrExport(stmt) {
      if (stmt.type === "ImportDeclaration" || stmt.type === "ExportAllDeclaration") {
        return true;
      }
      if (stmt.type === "ExportNamedDeclaration" || stmt.type === "ExportDefaultDeclaration") {
        const exportStmt = stmt;
        return exportStmt.declaration === null;
      }
      return false;
    }
    function isSimpleStatement(stmt) {
      const stmtType = stmt.type;
      if (stmtType === "TSTypeAliasDeclaration" || stmtType === "TSInterfaceDeclaration") {
        return true;
      }
      if (stmt.type === "VariableDeclaration") {
        const varDecl = stmt;
        for (const decl of varDecl.declarations) {
          if (decl.init && decl.init.type !== "Literal" && decl.init.type !== "Identifier") {
            return false;
          }
        }
        return true;
      }
      return false;
    }
    function hasComplexLogic(stmt) {
      if (stmt.type === "FunctionDeclaration") {
        return { has: true, type: "function definition" };
      }
      if (stmt.type === "ClassDeclaration") {
        return { has: true, type: "class definition" };
      }
      if (stmt.type === "IfStatement" || stmt.type === "ForStatement" || stmt.type === "WhileStatement") {
        return { has: true, type: "control flow statement" };
      }
      if (stmt.type === "TryStatement") {
        return { has: true, type: "try-catch block" };
      }
      if (stmt.type === "VariableDeclaration") {
        const varDecl = stmt;
        for (const decl of varDecl.declarations) {
          if (decl.init) {
            if (decl.init.type === "FunctionExpression" || decl.init.type === "ArrowFunctionExpression" || decl.init.type === "ClassExpression") {
              return { has: true, type: "function/class expression" };
            }
          }
        }
      }
      return { has: false, type: "" };
    }
    return {
      Program(node) {
        const program = node;
        const statements = program.body;
        let nonImportExportCount = 0;
        const complexLogicItems = [];
        for (const stmt of statements) {
          if (!isImportOrExport(stmt) && !isSimpleStatement(stmt)) {
            nonImportExportCount++;
            const complexCheck = hasComplexLogic(stmt);
            if (complexCheck.has) {
              const stmtNode = stmt;
              complexLogicItems.push({
                type: complexCheck.type,
                line: stmtNode.loc?.start.line || 0
              });
            }
          }
        }
        if (complexLogicItems.length > 0) {
          for (const item of complexLogicItems) {
            context.report({
              node,
              messageId: "hasComplexLogic",
              data: {
                filename: filename.replace(/\\/g, "/").split("/").pop() || filename,
                type: item.type
              }
            });
          }
        }
        if (nonImportExportCount > maxStatements) {
          context.report({
            node,
            messageId: "tooMuchLogic",
            data: {
              filename: filename.replace(/\\/g, "/").split("/").pop() || filename,
              count: String(nonImportExportCount),
              max: String(maxStatements)
            }
          });
        }
      }
    };
  }
};

// dist/index.js
var rules = {
  "require-schema-validation": requireSchemaValidation,
  "no-io-in-core": noIoInCore,
  "shell-result-type": shellResultType,
  "no-any-in-schema": noAnyInSchema,
  "require-jsdoc-example": requireJsdocExample,
  "max-file-lines": maxFileLines,
  "max-function-lines": maxFunctionLines,
  "no-empty-schema": noEmptySchema,
  "no-redundant-type-schema": noRedundantTypeSchema,
  "require-complete-validation": requireCompleteValidation,
  "no-runtime-imports": noRuntimeImports,
  "no-impure-calls-in-core": noImpureCallsInCore,
  "no-pure-logic-in-shell": noPureLogicInShell,
  "shell-complexity": shellComplexity,
  "thin-entry-points": thinEntryPoints
};
var configs = {
  recommended: {
    plugins: ["@invar"],
    rules: {
      "@invar/require-schema-validation": ["error", { mode: "recommended" }],
      "@invar/no-io-in-core": "error",
      "@invar/shell-result-type": "warn",
      "@invar/no-any-in-schema": "warn",
      "@invar/require-jsdoc-example": "error",
      "@invar/max-file-lines": "error",
      "@invar/max-function-lines": "error",
      "@invar/no-empty-schema": "error",
      "@invar/no-redundant-type-schema": "warn",
      "@invar/require-complete-validation": "warn",
      "@invar/no-runtime-imports": "error",
      "@invar/no-impure-calls-in-core": "error",
      "@invar/no-pure-logic-in-shell": "warn",
      "@invar/shell-complexity": "warn",
      "@invar/thin-entry-points": "warn"
    }
  },
  strict: {
    plugins: ["@invar"],
    rules: {
      "@invar/require-schema-validation": ["error", { mode: "strict" }],
      "@invar/no-io-in-core": "error",
      "@invar/shell-result-type": "error",
      "@invar/no-any-in-schema": "error",
      "@invar/require-jsdoc-example": "error",
      "@invar/max-file-lines": "error",
      "@invar/max-function-lines": "error",
      "@invar/no-empty-schema": "error",
      "@invar/no-redundant-type-schema": "error",
      "@invar/require-complete-validation": "error",
      "@invar/no-runtime-imports": "error",
      "@invar/no-impure-calls-in-core": "error",
      "@invar/no-pure-logic-in-shell": "error",
      "@invar/shell-complexity": "error",
      "@invar/thin-entry-points": "error"
    }
  }
};
var plugin = {
  rules,
  configs
  // Type assertion due to ESLint config type complexity
};
var dist_default = plugin;

// dist/cli.js
var import_meta = {};
function parseArgs(args) {
  const projectPath = args.find((arg) => !arg.startsWith("--")) || ".";
  const configArg = args.find((arg) => arg.startsWith("--config="));
  const config = configArg?.split("=")[1] === "strict" ? "strict" : "recommended";
  const help = args.includes("--help") || args.includes("-h");
  return { projectPath, config, help };
}
function printHelp() {
  console.log(`
@invar/eslint-plugin - ESLint with Invar-specific rules

Usage:
  node cli.js [path] [options]

Arguments:
  path              Project directory to lint (default: current directory)

Options:
  --config=MODE     Use 'recommended' or 'strict' preset (default: recommended)
  --help, -h        Show this help message

Examples:
  node cli.js                           # Lint current directory (recommended mode)
  node cli.js ./src                     # Lint specific directory
  node cli.js --config=strict           # Use strict mode (all rules as errors)

Output:
  JSON format compatible with ESLint's --format=json
  Exit code 0 if no errors, 1 if errors found
`);
}
async function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    printHelp();
    process.exit(0);
  }
  const projectPath = (0, import_path.resolve)(args.projectPath);
  const cwd = process.cwd();
  if (!projectPath.startsWith(cwd) && !projectPath.startsWith("/")) {
    console.error(`Error: Project path must be within current directory`);
    console.error(`  Requested: ${args.projectPath}`);
    console.error(`  Resolved: ${projectPath}`);
    console.error(`  Working dir: ${cwd}`);
    process.exit(1);
  }
  try {
    const selectedConfig = dist_default.configs?.[args.config];
    if (!selectedConfig || !selectedConfig.rules) {
      console.error(`Config "${args.config}" not found or invalid`);
      process.exit(1);
    }
    const __dirname = typeof __filename !== "undefined" ? (0, import_path.dirname)(__filename) : (0, import_path.dirname)((0, import_url.fileURLToPath)(import_meta.url));
    const eslint = new import_eslint.ESLint({
      useEslintrc: false,
      // Don't load .eslintrc files
      resolvePluginsRelativeTo: __dirname,
      // Tell ESLint where to find parser/plugins
      baseConfig: {
        parser: "@typescript-eslint/parser",
        // String path resolved from resolvePluginsRelativeTo
        parserOptions: {
          ecmaVersion: 2022,
          sourceType: "module"
        },
        plugins: ["@invar"],
        rules: selectedConfig.rules
      },
      plugins: {
        "@invar": dist_default
        // Register our plugin programmatically
      }
    });
    const results = await eslint.lintFiles([projectPath]);
    const formatter = await eslint.loadFormatter("json");
    const resultText = await Promise.resolve(formatter.format(results, {
      cwd: projectPath,
      rulesMeta: eslint.getRulesMetaForResults(results)
    }));
    console.log(resultText);
    const hasErrors = results.some((result) => result.errorCount > 0);
    process.exit(hasErrors ? 1 : 0);
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "Unknown error";
    console.error(`ESLint failed: ${errorMessage}`);
    process.exit(1);
  }
}
main();
