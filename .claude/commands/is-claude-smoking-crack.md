# Reality Check Validation Command

This command validates Claude's claims by actually testing functionality rather than assuming success.

## Usage
```
/is-claude-smoking-crack [component]
```

## What it checks
- File existence and content validation
- Endpoint functionality testing  
- Service availability verification
- Code execution validation
- Claims vs reality comparison

## Components
- `ui` - Test UI components and endpoints
- `claude` - Validate Claude integration
- `session` - Check session management  
- `logs` - Verify logging functionality
- `all` - Comprehensive validation (default)

## Purpose
Catch hallucinations, overpromises, and "Perfect!" declarations that aren't actually perfect.