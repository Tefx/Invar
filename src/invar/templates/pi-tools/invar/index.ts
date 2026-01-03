/**
 * Invar Custom Tools for Pi Coding Agent
 *
 * Wraps Invar CLI commands as Pi tools for better LLM integration.
 * Installed via: invar init --pi
 */

import { Type } from "@sinclair/typebox";
import type { CustomToolFactory } from "@mariozechner/pi-coding-agent";

const factory: CustomToolFactory = (pi) => {
  // Helper to check if invar is available
  async function checkInvarInstalled(): Promise<boolean> {
    try {
      const result = await pi.exec("which", ["invar"]);
      return result.exitCode === 0;
    } catch {
      return false;
    }
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
        const installed = await checkInvarInstalled();
        if (!installed) {
          throw new Error("Invar not installed. Run: pip install invar-tools");
        }

        const args = ["guard"];

        // Default is --changed (check modified files)
        if (params.changed === false) {
          args.push("--all");
        }

        if (params.contracts_only) {
          args.push("-c");
        }
        if (params.coverage) {
          args.push("--coverage");
        }
        if (params.strict) {
          args.push("--strict");
        }

        const result = await pi.exec("invar", args, { cwd: pi.cwd, signal });

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
        const installed = await checkInvarInstalled();
        if (!installed) {
          throw new Error("Invar not installed. Run: pip install invar-tools");
        }

        const result = await pi.exec("invar", ["sig", params.target], {
          cwd: pi.cwd,
          signal,
        });

        if (result.killed) {
          throw new Error("Sig command was cancelled");
        }

        if (result.exitCode !== 0) {
          throw new Error(`Failed to get signatures: ${result.stderr}`);
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
        const installed = await checkInvarInstalled();
        if (!installed) {
          throw new Error("Invar not installed. Run: pip install invar-tools");
        }

        const args = ["map"];

        if (params.path && params.path !== ".") {
          args.push(params.path);
        }

        if (params.top) {
          args.push("--top", params.top.toString());
        }

        const result = await pi.exec("invar", args, {
          cwd: pi.cwd,
          signal,
        });

        if (result.killed) {
          throw new Error("Map command was cancelled");
        }

        if (result.exitCode !== 0) {
          throw new Error(`Failed to generate map: ${result.stderr}`);
        }

        return {
          content: [{ type: "text", text: result.stdout }],
          details: {
            path: params.path || ".",
            top: params.top || 10,
          },
        };
      },
    },
  ];
};

export default factory;
