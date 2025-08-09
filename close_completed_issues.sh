#!/bin/bash
# Close completed issues with proper documentation

echo "Closing completed issues..."

# Close all completed issues
for issue in 23 24 22 15 14 13 17; do
    case $issue in
        23)
            title="MCP Client"
            evidence="src/mcp_client/ directory with full implementation"
            ;;
        24)
            title="Gmail Integration"
            evidence="src/mcp_tools/gmail_tool.py"
            ;;
        22)
            title="Google Nest Integration"
            evidence="src/mcp_tools/nest_tool.py"
            ;;
        15)
            title="Telegram Bot"
            evidence="src/mcp_server/telegram_bot.py"
            ;;
        14)
            title="Web Interface"
            evidence="static/ directory with HTML files"
            ;;
        13)
            title="Authentication"
            evidence="src/mcp_server/auth.py and related files"
            ;;
        17)
            title="User Onboarding"
            evidence="src/mcp_server/onboarding.py and beta_onboarding.py"
            ;;
    esac
    
    echo "Closing issue #${issue}: ${title}"
    gh issue comment $issue --body "🤖 Feature completed. Evidence: ${evidence}"
    gh issue close $issue
done

echo "All completed issues closed!"