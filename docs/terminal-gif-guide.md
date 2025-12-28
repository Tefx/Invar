# Creating Terminal Demo GIFs for Invar

This guide shows how to create professional terminal animations for the README.

---

## Option 1: asciinema + agg (Recommended)

Best for: High-quality, small file size, reproducible recordings.

### Step 1: Install Tools

```bash
# macOS
brew install asciinema
pip install agg  # or: cargo install agg

# Linux
sudo apt install asciinema
pip install agg
```

### Step 2: Record Terminal Session

```bash
# Start recording
asciinema rec demo.cast

# Now perform your demo actions:
# 1. Show a simple Python file with contracts
cat src/core/math.py

# 2. Run invar guard
invar guard

# 3. Show an error case and fix
# ... (edit file, re-run guard)

# Press Ctrl+D or type 'exit' to stop recording
```

### Step 3: Edit Recording (Optional)

```bash
# View the recording
asciinema play demo.cast

# Edit timing (if needed)
# The .cast file is JSON - you can manually adjust frame timings
```

### Step 4: Convert to GIF

```bash
# Basic conversion
agg demo.cast demo.gif

# With options (recommended)
agg demo.cast demo.gif \
  --font-size 14 \
  --cols 80 \
  --rows 24 \
  --theme monokai

# Speed up (1.5x faster)
agg demo.cast demo.gif --speed 1.5
```

### Step 5: Optimize GIF Size

```bash
# Install gifsicle
brew install gifsicle  # macOS
# or: sudo apt install gifsicle  # Linux

# Optimize
gifsicle -O3 --colors 64 demo.gif -o demo-optimized.gif
```

---

## Option 2: Terminalizer

Best for: Easy customization, built-in themes.

### Step 1: Install

```bash
npm install -g terminalizer
```

### Step 2: Configure

```bash
# Generate config
terminalizer init

# Edit terminalizer config (terminalizer.config.yml)
# Key settings:
#   cols: 80
#   rows: 24
#   theme: "monokai"
#   frameDelay: 100
```

### Step 3: Record

```bash
terminalizer record demo
# Perform your demo actions
# Press Ctrl+D to stop
```

### Step 4: Render

```bash
terminalizer render demo -o demo.gif
```

---

## Option 3: VHS (Scripted Recordings)

Best for: Reproducible, scripted demos.

### Step 1: Install

```bash
brew install vhs  # macOS
# or: go install github.com/charmbracelet/vhs@latest
```

### Step 2: Create Script

Create `demo.tape`:

```tape
# Demo settings
Output demo.gif
Set FontSize 14
Set Width 800
Set Height 600
Set Theme "Monokai"

# Commands
Type "cat src/core/math.py"
Enter
Sleep 2s

Type "invar guard"
Enter
Sleep 3s

Type "# All checks passed!"
Enter
Sleep 1s
```

### Step 3: Run

```bash
vhs demo.tape
```

---

## Recommended Demo Script

Here's what to show in the Invar demo GIF:

### Scene 1: Show Contract Code (3s)
```bash
$ cat src/core/math.py
```
Display the average function with `@pre`, `@post`, and doctests.

### Scene 2: Run Guard - Success (4s)
```bash
$ invar guard
```
Show the full Guard report with "Guard passed."

### Scene 3: Introduce Error (3s)
```bash
$ # Remove a doctest...
$ invar guard --changed
```
Show warning about missing doctest.

### Scene 4: Fix and Verify (4s)
```bash
$ # Add doctest back...
$ invar guard --changed
Guard passed.
```

**Total: ~15 seconds**

---

## File Placement

```
docs/
├── assets/
│   ├── demo.gif          # Main demo for README
│   ├── guard-demo.gif    # Guard-specific demo
│   └── workflow-demo.gif # USBV workflow demo
└── terminal-gif-guide.md # This file
```

## README Integration

```markdown
### What It Looks Like

![Invar Demo](./docs/assets/demo.gif)
```

---

## Quality Checklist

- [ ] GIF is under 5MB (GitHub limit)
- [ ] Text is readable at 100% zoom
- [ ] Recording is 10-20 seconds max
- [ ] Terminal window is 80x24 characters
- [ ] Uses consistent color theme
- [ ] Shows realistic, working commands
- [ ] Includes brief pauses for readability
