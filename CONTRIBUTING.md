# Contributing to ADHDo 🤝

*Making it easy for agents and developers to contribute effectively*

## 🚀 **Quick Start for Agents**

### **Creating Issues**
Use our helper script for consistent issue creation:

```bash
# Feature requests
./scripts/issue_helpers.sh feature "Add voice input" "Allow users to speak their requests"

# Bug reports  
./scripts/issue_helpers.sh bug "Chat fails on empty input" "API returns 500 error" "1. Send empty message 2. See error"

# Performance issues
./scripts/issue_helpers.sh performance "Optimize LLM response time" "5-6 seconds" "< 2 seconds"

# Domain expansion
./scripts/issue_helpers.sh domain "MCP-Therapy" "Mental health professionals"

# View project status
./scripts/issue_helpers.sh status
```

### **Issue Labels**
- `phase-1` - Current development phase (production readiness)
- `phase-2` - Next phase (domain expansion)
- `performance` - Performance optimizations
- `security` - Security and safety features
- `mcp-core` - Core MCP framework
- `domain-expansion` - New domain development
- `llm` - LLM and AI features
- `redis` - Redis integration
- `architecture` - Architecture and design

### **Development Workflow**
1. **Check issues**: `gh issue list --label phase-1`
2. **Create branch**: `git checkout -b feature/issue-name`
3. **Develop**: Write code, tests, documentation
4. **Test**: Run test suites and performance benchmarks
5. **Commit**: Use conventional commits with issue references
6. **PR**: Create pull request linking to issue
7. **Review**: Address feedback and merge

## 📋 **Project Structure**

### **Core Components**
```
src/
├── mcp_server/          # FastAPI server and cognitive loop
│   ├── main.py         # API endpoints and lifespan management
│   ├── cognitive_loop.py # Core MCP processing engine
│   ├── llm_client.py   # LLM routing and optimization
│   ├── models.py       # Pydantic data models
│   └── config.py       # Configuration management
├── frames/             # Context building and cognitive load
│   └── builder.py      # Contextual frame assembly
├── traces/             # Memory and pattern learning
│   └── memory.py       # Redis-based trace memory
└── nudge/              # Notification and engagement
    └── engine.py       # Multi-modal nudge system
```

### **Configuration Files**
- `pyproject.toml` - Python package configuration
- `docker-compose.yml` - Development environment
- `requirements.txt` - Python dependencies
- `.env.example` - Environment variable template

### **Documentation**
- `MCP_ARCHITECTURE.md` - Technical architecture overview
- `PLATFORM_STRATEGY.md` - Multi-domain expansion strategy
- `MONETIZATION_ROADMAP.md` - Business model and revenue streams
- `NEXT_STEPS.md` - Development roadmap and current status

## 🧪 **Testing**

### **Test Scripts**
```bash
# Test core functionality
python test_server.py

# Test Redis integration
python test_redis_connection.py

# Performance benchmarks
python test_performance.py

# Demo the full system
python demo_server.py
```

### **Performance Targets**
- **Response time**: < 3 seconds
- **Crisis detection**: < 1 second
- **Cache hits**: < 1ms
- **Context building**: < 200ms

## 🔒 **Safety & Security**

### **Crisis Detection**
All crisis patterns are hard-coded responses (never LLM-generated):
- Self-harm indicators → Crisis hotlines and resources
- Substance abuse triggers → Recovery support contacts
- Therapeutic rupture → Professional escalation protocols

### **Privacy by Design**
- Local-first processing when possible
- Redis for hot data, PostgreSQL for warm data
- No sensitive data in logs or caches
- User consent for all data collection

## 🎯 **Contribution Guidelines**

### **Code Quality**
- **Type hints**: All functions must have type annotations
- **Docstrings**: Use Google-style docstrings for classes and methods
- **Testing**: Write tests for all new functionality
- **Performance**: Profile and benchmark performance-critical code

### **Commit Messages**
Use conventional commits with issue references:
```
feat: add user authentication endpoints (#1)
fix: resolve Redis connection timeout (#3)  
perf: optimize LLM response caching (#3)
docs: update API documentation
```

### **Pull Request Process**
1. **Link to issue**: Reference the issue being addressed
2. **Description**: Explain what changed and why
3. **Testing**: Include test results and performance impact
4. **Documentation**: Update relevant documentation
5. **Breaking changes**: Clearly mark any breaking changes

## 🌍 **Domain Development**

### **Adding New Domains**
When implementing a new MCP domain (e.g., MCP-Therapy):

1. **Research phase**: User interviews, market analysis, technical requirements
2. **Configuration**: Define domain-specific crisis patterns, context types, cognitive load limits
3. **Implementation**: Create domain adapter, context builders, safety protocols
4. **Validation**: User testing, clinical validation (if applicable), performance benchmarking
5. **Launch**: Go-to-market strategy, user onboarding, professional partnerships

### **Domain Checklist**
- [ ] Domain configuration file
- [ ] Crisis pattern definitions
- [ ] Context type implementations
- [ ] Safety protocol adaptations
- [ ] LLM prompt customizations
- [ ] User research validation
- [ ] Performance benchmarking
- [ ] Documentation and guides

## 📞 **Getting Help**

### **For Agents**
- **Issue management**: Use `./scripts/issue_helpers.sh help`
- **Project status**: Run `./scripts/issue_helpers.sh status`
- **Architecture questions**: See `MCP_ARCHITECTURE.md`
- **Performance issues**: Check `test_performance.py` results

### **For Contributors**
- **GitHub Discussions**: Ask questions and share ideas
- **Issues**: Report bugs and request features
- **Pull Requests**: Contribute code and improvements
- **Documentation**: Help improve guides and examples

## 🎉 **Recognition**

Contributors to ADHDo are building something that could genuinely improve lives for millions of neurodivergent people. Every contribution - whether code, documentation, testing, or feedback - helps create a more inclusive and supportive digital world.

Thank you for being part of this mission! 🧠⚡

---

*Last updated: $(date +'%Y-%m-%d')*