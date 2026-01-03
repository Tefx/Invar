/**
 * Invar Custom Tools for Pi Coding Agent
 *
 * Wraps Invar CLI commands as Pi tools for better LLM integration.
 * Installed via: invar init --pi
 */

import { Type } from "@sinclair/typebox";
import type { CustomToolFactory } from "@mariozechner/pi-coding-agent";
import * as fs from "fs";
import * as path from "path";

const factory: CustomToolFactory = (pi) => {
  // Helper to resolve invar command (with uvx fallback)
  async function resolveInvarCommand(): Promise<{ command: string; args: string[] }> {
    // Try direct invar command first
    try {
      const result = await pi.exec("which", ["invar"]);
      if (result.exitCode === 0) {
        return { command: "invar", args: [] };
      }
    } catch {
      // Fall through to uvx
    }

    // Fallback to uvx invar-tools
    return { command: "uvx", args: ["invar-tools"] };
  }

  // Helper to validate path/target parameters (defense-in-depth)
  function isValidPath(p: string): boolean {
    // Reject shell metacharacters (including newline injection) and path traversal
    if (/[;&|`$"'\\<>\n\r\0]/.test(p)) {
      return false;
    }
    if (p.includes('..')) {
      return false;
    }
    return true;
  }

  return [
    // =========================================================================
    // invar_guard - Smart verification (static + doctests + symbolic)
    // =========================================================================
    {
      name: "invar_guard",
      label: "Invar Guard",
      description: "Verify code quality with static analysis, doctests, CrossHair symbolic execution, and Hypothesis testing. Use this instead of pytest/crosshair. By default checks git-modified files; use --all for full project check.",
      parameters: Type.Object({
        changed: Type.Optional(Type.Boolean({
          description: "Check only git-modified files (default: true)",
          default: true,
        })),
        contracts_only: Type.Optional(Type.Boolean({
          description: "Contract coverage check only (skip tests)",
          default: false,
        })),
        coverage: Type.Optional(Type.Boolean({
          description: "Collect branch coverage from doctest + hypothesis",
          default: false,
        })),
        strict: Type.Optional(Type.Boolean({
          description: "Treat warnings as errors",
          default: false,
        })),
      }),
      async execute(toolCallId, params, onUpdate, ctx, signal) {
        const cmd = await resolveInvarCommand();
        const args = [...cmd.args, "guard"];

        // Handle optional parameters with defaults
        const changed = params.changed ?? true;
        const contractsOnly = params.contracts_only ?? false;
        const coverage = params.coverage ?? false;
        const strict = params.strict ?? false;

        // Default is --changed (check modified files)
        if (changed === false) {
          args.push("--all");
        }

        if (contractsOnly) {
          args.push("-c");
        }
        if (coverage) {
          args.push("--coverage");
        }
        if (strict) {
          args.push("--strict");
        }

        const result = await pi.exec(cmd.command, args, { cwd: pi.cwd, signal });

        if (result.killed) {
          throw new Error("Guard verification was cancelled");
        }

        const output = result.stdout + result.stderr;

        return {
          content: [{ type: "text", text: output || "Guard completed" }],
          details: {
            exitCode: result.exitCode,
            passed: result.exitCode === 0,
          },
        };
      },
    },

    // =========================================================================
    // invar_sig - Show function signatures and contracts
    // =========================================================================
    {
      name: "invar_sig",
      label: "Invar Sig",
      description: "Show function signatures and contracts (@pre/@post). Use this INSTEAD of Read() when you want to understand file structure without reading full implementation.",
      parameters: Type.Object({
        target: Type.String({
          description: "File path or file::symbol path (e.g., 'src/foo.py' or 'src/foo.py::MyClass')",
        }),
      }),
      async execute(toolCallId, params, onUpdate, ctx, signal) {
        const cmd = await resolveInvarCommand();

        // Validate required parameter
        if (!params.target) {
          throw new Error("Missing required parameter: target (file path or file::symbol)");
        }

        if (!isValidPath(params.target)) {
          throw new Error("Invalid target path: contains unsafe characters or path traversal");
        }

        const result = await pi.exec(cmd.command, [...cmd.args, "sig", params.target], {
          cwd: pi.cwd,
          signal,
        });

        if (result.killed) {
          throw new Error("Sig command was cancelled");
        }

        // Only treat as error if exitCode is explicitly non-zero
        // (Pi's exec may return undefined/null for success)
        if (result.exitCode && result.exitCode !== 0) {
          const errorMsg = result.stderr || result.stdout || "Unknown error";
          throw new Error(`Failed to get signatures: ${errorMsg}`);
        }

        return {
          content: [{ type: "text", text: result.stdout }],
          details: {
            target: params.target,
          },
        };
      },
    },

    // =========================================================================
    // invar_map - Symbol map with reference counts
    // =========================================================================
    {
      name: "invar_map",
      label: "Invar Map",
      description: "Symbol map with reference counts. Use this INSTEAD of Grep for 'def ' to find entry points and most-referenced symbols.",
      parameters: Type.Object({
        path: Type.Optional(Type.String({
          description: "Project path (default: current directory)",
          default: ".",
        })),
        top: Type.Optional(Type.Number({
          description: "Show top N symbols by reference count",
          default: 10,
        })),
      }),
      async execute(toolCallId, params, onUpdate, ctx, signal) {
        const cmd = await resolveInvarCommand();

        // Handle optional parameters with defaults
        const targetPath = params.path ?? ".";
        const topN = params.top ?? 10;

        if (targetPath !== "." && !isValidPath(targetPath)) {
          throw new Error("Invalid path: contains unsafe characters or path traversal");
        }

        const args = [...cmd.args, "map"];

        if (targetPath !== ".") {
          args.push(targetPath);
        }

        args.push("--top", topN.toString());

        const result = await pi.exec(cmd.command, args, {
          cwd: pi.cwd,
          signal,
        });

        if (result.killed) {
          throw new Error("Map command was cancelled");
        }

        // Only treat as error if exitCode is explicitly non-zero
        if (result.exitCode && result.exitCode !== 0) {
          const errorMsg = result.stderr || result.stdout || "Unknown error";
          throw new Error(`Failed to generate map: ${errorMsg}`);
        }

        return {
          content: [{ type: "text", text: result.stdout }],
          details: {
            path: targetPath,
            top: topN,
          },
        };
      },
    },

    // =========================================================================
    // invar_doc_toc - Extract document structure (Table of Contents)
    // =========================================================================
    {
      name: "invar_doc_toc",
      label: "Invar Doc TOC",
      description: "Extract document structure (Table of Contents) from markdown files. Shows headings hierarchy with line numbers and character counts. Use this INSTEAD of Read() to understand markdown structure.",
      parameters: Type.Object({
        file: Type.String({
          description: "Path to markdown file",
        }),
        depth: Type.Optional(Type.Number({
          description: "Maximum heading depth to include (1-6)",
          default: 6,
          minimum: 1,
          maximum: 6,
        })),
      }),
      async execute(toolCallId, params, onUpdate, ctx, signal) {
        const cmd = await resolveInvarCommand();

        // Validate required parameter
        if (!params.file) {
          throw new Error("Missing required parameter: file (markdown file path)");
        }

        if (!isValidPath(params.file)) {
          throw new Error("Invalid file path: contains unsafe characters or path traversal");
        }

        // Handle optional parameter with default
        const maxDepth = params.depth ?? 6;

        const args = [...cmd.args, "doc", "toc", params.file];

        if (maxDepth !== 6) {
          args.push("--depth", maxDepth.toString());
        }

        const result = await pi.exec(cmd.command, args, {
          cwd: pi.cwd,
          signal,
        });

        if (result.killed) {
          throw new Error("Doc toc command was cancelled");
        }

        // Only treat as error if exitCode is explicitly non-zero
        if (result.exitCode && result.exitCode !== 0) {
          const errorMsg = result.stderr || result.stdout || "Unknown error";
          throw new Error(`Failed to extract TOC: ${errorMsg}`);
        }

        return {
          content: [{ type: "text", text: result.stdout }],
          details: {
            file: params.file,
            depth: maxDepth,
          },
        };
      },
    },

    // =========================================================================
    // invar_doc_read - Read a specific section from a document
    // =========================================================================
    {
      name: "invar_doc_read",
      label: "Invar Doc Read",
      description: "Read a specific section from a markdown document. Supports multiple addressing formats: slug path, fuzzy match, index (#0/#1), or line anchor (@48). Use this INSTEAD of Read() with manual line counting.",
      parameters: Type.Object({
        file: Type.String({
          description: "Path to markdown file",
        }),
        section: Type.String({
          description: "Section path: slug ('requirements/auth'), fuzzy ('auth'), index ('#0/#1'), or line ('@48')",
        }),
        children: Type.Optional(Type.Boolean({
          description: "Include child sections in output",
          default: true,
        })),
      }),
      async execute(toolCallId, params, onUpdate, ctx, signal) {
        const cmd = await resolveInvarCommand();

        // Validate required parameters
        if (!params.file) {
          throw new Error("Missing required parameter: file (markdown file path)");
        }
        if (!params.section) {
          throw new Error("Missing required parameter: section (section path or identifier)");
        }

        if (!isValidPath(params.file) || !isValidPath(params.section)) {
          throw new Error("Invalid file or section path: contains unsafe characters or path traversal");
        }

        // Handle optional parameter with default
        const includeChildren = params.children ?? true;

        const args = [...cmd.args, "doc", "read", params.file, params.section, "--json"];

        if (includeChildren === false) {
          args.push("--no-children");
        }

        const result = await pi.exec(cmd.command, args, {
          cwd: pi.cwd,
          signal,
        });

        if (result.killed) {
          throw new Error("Doc read command was cancelled");
        }

        // Only treat as error if exitCode is explicitly non-zero
        if (result.exitCode && result.exitCode !== 0) {
          const errorMsg = result.stderr || result.stdout || "Unknown error";
          throw new Error(`Failed to read section: ${errorMsg}`);
        }

        return {
          content: [{ type: "text", text: result.stdout }],
          details: {
            file: params.file,
            section: params.section,
          },
        };
      },
    },

    // =========================================================================
    // invar_doc_find - Find sections matching a pattern
    // =========================================================================
    {
      name: "invar_doc_find",
      label: "Invar Doc Find",
      description: "Find sections in markdown documents matching a pattern. Supports glob patterns for titles and optional content search. Use this INSTEAD of Grep in markdown files.",
      parameters: Type.Object({
        file: Type.String({
          description: "Path to markdown file",
        }),
        pattern: Type.String({
          description: "Title pattern (glob-style, e.g., '*auth*')",
        }),
        content: Type.Optional(Type.String({
          description: "Optional content search pattern",
        })),
        level: Type.Optional(Type.Number({
          description: "Filter by heading level (1-6)",
          minimum: 1,
          maximum: 6,
        })),
      }),
      async execute(toolCallId, params, onUpdate, ctx, signal) {
        const cmd = await resolveInvarCommand();

        // Validate required parameters
        if (!params.file) {
          throw new Error("Missing required parameter: file (markdown file path)");
        }
        if (!params.pattern) {
          throw new Error("Missing required parameter: pattern (glob pattern for section titles)");
        }

        if (!isValidPath(params.file)) {
          throw new Error("Invalid file path: contains unsafe characters or path traversal");
        }

        const args = [...cmd.args, "doc", "find", params.pattern, params.file, "--json"];

        // Handle optional parameters
        if (params.content) {
          args.push("--content", params.content);
        }

        if (params.level) {
          args.push("--level", params.level.toString());
        }

        const result = await pi.exec(cmd.command, args, {
          cwd: pi.cwd,
          signal,
        });

        if (result.killed) {
          throw new Error("Doc find command was cancelled");
        }

        // Only treat as error if exitCode is explicitly non-zero
        if (result.exitCode && result.exitCode !== 0) {
          const errorMsg = result.stderr || result.stdout || "Unknown error";
          throw new Error(`Failed to find sections: ${errorMsg}`);
        }

        return {
          content: [{ type: "text", text: result.stdout }],
          details: {
            file: params.file,
            pattern: params.pattern,
          },
        };
      },
    },

    // =========================================================================
    // invar_doc_replace - Replace a section's content
    // =========================================================================
    {
      name: "invar_doc_replace",
      label: "Invar Doc Replace",
      description: "Replace a section's content in a markdown document. Use this INSTEAD of Edit()/Write() for section replacement.",
      parameters: Type.Object({
        file: Type.String({
          description: "Path to markdown file",
        }),
        section: Type.String({
          description: "Section path to replace (slug, fuzzy, index, or line anchor)",
        }),
        content: Type.String({
          description: "New content to replace the section with",
        }),
        keep_heading: Type.Optional(Type.Boolean({
          description: "If true, preserve the original heading line",
          default: true,
        })),
      }),
      async execute(toolCallId, params, onUpdate, ctx, signal) {
        const cmd = await resolveInvarCommand();

        // Validate required parameters
        if (!params.file) {
          throw new Error("Missing required parameter: file (markdown file path)");
        }
        if (!params.section) {
          throw new Error("Missing required parameter: section (section path or identifier)");
        }
        if (!params.content) {
          throw new Error("Missing required parameter: content (new content for section)");
        }

        if (!isValidPath(params.file) || !isValidPath(params.section)) {
          throw new Error("Invalid file or section path: contains unsafe characters or path traversal");
        }

        // Handle optional parameter with default
        const keepHeading = params.keep_heading ?? true;

        // Write content to temporary file to avoid shell injection
        const tmpFile = path.join(pi.cwd, `.invar-tmp-${Date.now()}.txt`);

        try {
          fs.writeFileSync(tmpFile, params.content, "utf-8");

          const args = [
            ...cmd.args,
            "doc",
            "replace",
            params.file,
            params.section,
            "--content",
            tmpFile,
          ];

          if (keepHeading === false) {
            args.push("--no-keep-heading");
          }

          const result = await pi.exec(cmd.command, args, {
            cwd: pi.cwd,
            signal,
          });

          if (result.killed) {
            throw new Error("Doc replace command was cancelled");
          }

          // Only treat as error if exitCode is explicitly non-zero
          if (result.exitCode && result.exitCode !== 0) {
            const errorMsg = result.stderr || result.stdout || "Unknown error";
            throw new Error(`Failed to replace section: ${errorMsg}`);
          }

          return {
            content: [{ type: "text", text: result.stdout || "Section replaced successfully" }],
            details: {
              file: params.file,
              section: params.section,
            },
          };
        } finally {
          // Clean up temp file
          try {
            fs.unlinkSync(tmpFile);
          } catch {
            // Ignore cleanup errors
          }
        }
      },
    },

    // =========================================================================
    // invar_doc_insert - Insert new content relative to a section
    // =========================================================================
    {
      name: "invar_doc_insert",
      label: "Invar Doc Insert",
      description: "Insert new content relative to a section in a markdown document. Use this INSTEAD of Edit()/Write() for section insertion.",
      parameters: Type.Object({
        file: Type.String({
          description: "Path to markdown file",
        }),
        anchor: Type.String({
          description: "Section path for the anchor (slug, fuzzy, index, or line anchor)",
        }),
        content: Type.String({
          description: "Content to insert (include heading if new section)",
        }),
        position: Type.Optional(Type.String({
          description: "Where to insert: 'before', 'after', 'first_child', 'last_child'",
          default: "after",
          enum: ["before", "after", "first_child", "last_child"],
        })),
      }),
      async execute(toolCallId, params, onUpdate, ctx, signal) {
        const cmd = await resolveInvarCommand();

        // Validate required parameters
        if (!params.file) {
          throw new Error("Missing required parameter: file (markdown file path)");
        }
        if (!params.anchor) {
          throw new Error("Missing required parameter: anchor (section path for insertion point)");
        }
        if (!params.content) {
          throw new Error("Missing required parameter: content (content to insert)");
        }

        if (!isValidPath(params.file) || !isValidPath(params.anchor)) {
          throw new Error("Invalid file or anchor path: contains unsafe characters or path traversal");
        }

        // Handle optional parameter with default
        const position = params.position ?? "after";

        // Write content to temporary file
        const tmpFile = path.join(pi.cwd, `.invar-tmp-${Date.now()}.txt`);

        try {
          fs.writeFileSync(tmpFile, params.content, "utf-8");

          const args = [
            ...cmd.args,
            "doc",
            "insert",
            params.file,
            params.anchor,
            "--content",
            tmpFile,
          ];

          if (position !== "after") {
            args.push("--position", position);
          }

          const result = await pi.exec(cmd.command, args, {
            cwd: pi.cwd,
            signal,
          });

          if (result.killed) {
            throw new Error("Doc insert command was cancelled");
          }

          // Only treat as error if exitCode is explicitly non-zero
          if (result.exitCode && result.exitCode !== 0) {
            const errorMsg = result.stderr || result.stdout || "Unknown error";
            throw new Error(`Failed to insert content: ${errorMsg}`);
          }

          return {
            content: [{ type: "text", text: result.stdout || "Content inserted successfully" }],
            details: {
              file: params.file,
              anchor: params.anchor,
              position: params.position || "after",
            },
          };
        } finally {
          // Clean up temp file
          try {
            fs.unlinkSync(tmpFile);
          } catch {
            // Ignore cleanup errors
          }
        }
      },
    },

    // =========================================================================
    // invar_doc_delete - Delete a section from a document
    // =========================================================================
    {
      name: "invar_doc_delete",
      label: "Invar Doc Delete",
      description: "Delete a section from a markdown document. Use this INSTEAD of Edit()/Write() for section deletion.",
      parameters: Type.Object({
        file: Type.String({
          description: "Path to markdown file",
        }),
        section: Type.String({
          description: "Section path to delete (slug, fuzzy, index, or line anchor)",
        }),
        children: Type.Optional(Type.Boolean({
          description: "Include child sections in deletion",
          default: true,
        })),
      }),
      async execute(toolCallId, params, onUpdate, ctx, signal) {
        const cmd = await resolveInvarCommand();

        // Validate required parameters
        if (!params.file) {
          throw new Error("Missing required parameter: file (markdown file path)");
        }
        if (!params.section) {
          throw new Error("Missing required parameter: section (section path or identifier)");
        }

        if (!isValidPath(params.file) || !isValidPath(params.section)) {
          throw new Error("Invalid file or section path: contains unsafe characters or path traversal");
        }

        // Handle optional parameter with default
        const includeChildren = params.children ?? true;

        const args = [...cmd.args, "doc", "delete", params.file, params.section];

        if (includeChildren === false) {
          args.push("--no-children");
        }

        const result = await pi.exec(cmd.command, args, {
          cwd: pi.cwd,
          signal,
        });

        if (result.killed) {
          throw new Error("Doc delete command was cancelled");
        }

        // Only treat as error if exitCode is explicitly non-zero
        if (result.exitCode && result.exitCode !== 0) {
          const errorMsg = result.stderr || result.stdout || "Unknown error";
          throw new Error(`Failed to delete section: ${errorMsg}`);
        }

        return {
          content: [{ type: "text", text: result.stdout || "Section deleted successfully" }],
          details: {
            file: params.file,
            section: params.section,
          },
        };
      },
    },
  ];
};

export default factory;
