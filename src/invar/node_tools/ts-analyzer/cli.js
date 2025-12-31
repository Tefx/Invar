#!/usr/bin/env node
// Mock CLI for testing embed workflow
const args = process.argv.slice(2);
if (args.includes('--help') || args.includes('-h')) {
  console.log(`@invar/${process.env.TOOL_NAME || 'unknown'} - Mock CLI for testing`);
  console.log('Usage: cli.js [options] [path]');
  console.log('Options:');
  console.log('  --json    Output JSON format');
  console.log('  --help    Show this help');
  process.exit(0);
}
if (args.includes('--json')) {
  console.log(JSON.stringify({
    status: 'ok',
    tool: process.env.TOOL_NAME || 'unknown',
    mock: true,
    path: args.find(a => !a.startsWith('-')) || '.'
  }));
} else {
  console.log('Mock tool executed successfully');
}
