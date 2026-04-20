#!/bin/bash
# Interactive Jira Setup Script for Weekly Status Agent

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_DIR/.env"
CONFIG_FILE="$PROJECT_DIR/config/config.yaml"

echo "=========================================="
echo "Jira Setup for Weekly Status Agent"
echo "=========================================="
echo

# Check if .env already exists
if [ -f "$ENV_FILE" ]; then
    echo "⚠️  .env file already exists at: $ENV_FILE"
    read -p "Do you want to update it? (y/n): " UPDATE_ENV
    if [ "$UPDATE_ENV" != "y" ]; then
        echo "Skipping .env creation. Using existing file."
        SKIP_ENV=true
    fi
fi

if [ "$SKIP_ENV" != "true" ]; then
    echo "Let's set up your Jira credentials."
    echo

    # Check if env vars are already set
    if [ -n "$JIRA_URL" ] && [ -n "$JIRA_EMAIL" ] && [ -n "$JIRA_API_TOKEN" ]; then
        echo "✓ Found Jira credentials in environment!"
        echo "  JIRA_URL: $JIRA_URL"
        echo "  JIRA_EMAIL: $JIRA_EMAIL"
        echo "  JIRA_API_TOKEN: ***"
        echo
        read -p "Use these credentials? (y/n): " USE_EXISTING

        if [ "$USE_EXISTING" = "y" ]; then
            JIRA_URL_INPUT="$JIRA_URL"
            JIRA_EMAIL_INPUT="$JIRA_EMAIL"
            JIRA_TOKEN_INPUT="$JIRA_API_TOKEN"
        fi
    fi

    # Prompt for Jira URL
    if [ -z "$JIRA_URL_INPUT" ]; then
        read -p "Jira URL (e.g., https://your-company.atlassian.net): " JIRA_URL_INPUT
        if [ -z "$JIRA_URL_INPUT" ]; then
            echo "Error: Jira URL is required"
            exit 1
        fi
    fi

    # Prompt for Jira email
    if [ -z "$JIRA_EMAIL_INPUT" ]; then
        read -p "Jira Email: " JIRA_EMAIL_INPUT
        if [ -z "$JIRA_EMAIL_INPUT" ]; then
            echo "Error: Jira email is required"
            exit 1
        fi
    fi

    # Prompt for Jira API token
    if [ -z "$JIRA_TOKEN_INPUT" ]; then
        echo
        echo "To get your Jira API token:"
        echo "  1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens"
        echo "  2. Click 'Create API token'"
        echo "  3. Copy the token and paste it here"
        echo
        read -sp "Jira API Token: " JIRA_TOKEN_INPUT
        echo
        if [ -z "$JIRA_TOKEN_INPUT" ]; then
            echo "Error: Jira API token is required"
            exit 1
        fi
    fi

    # Create .env file
    echo
    echo "Creating .env file..."
    cat > "$ENV_FILE" << EOF
# Jira Configuration
JIRA_URL=$JIRA_URL_INPUT
JIRA_EMAIL=$JIRA_EMAIL_INPUT
JIRA_API_TOKEN=$JIRA_TOKEN_INPUT

# AI Provider (optional - for weekly report generation)
# ANTHROPIC_API_KEY=your-key-here
# OPENAI_API_KEY=your-key-here
EOF

    chmod 600 "$ENV_FILE"
    echo "✓ Created .env file at: $ENV_FILE"
    echo
fi

# Set up config.yaml
if [ -f "$CONFIG_FILE" ]; then
    echo "⚠️  config.yaml already exists at: $CONFIG_FILE"
    read -p "Do you want to update it? (y/n): " UPDATE_CONFIG
    if [ "$UPDATE_CONFIG" != "y" ]; then
        echo "Skipping config.yaml creation. Using existing file."
        SKIP_CONFIG=true
    fi
fi

if [ "$SKIP_CONFIG" != "true" ]; then
    echo "Let's configure your Jira project settings."
    echo

    # Prompt for project keys
    read -p "Jira Project Key(s) (comma-separated, e.g., AIPCC,PROJ): " PROJECT_KEYS
    if [ -z "$PROJECT_KEYS" ]; then
        echo "Warning: No project keys specified. Using default 'PROJ'"
        PROJECT_KEYS="PROJ"
    fi

    # Convert comma-separated to YAML array format
    IFS=',' read -ra PROJECTS <<< "$PROJECT_KEYS"
    PROJECT_YAML="["
    for i in "${!PROJECTS[@]}"; do
        PROJECT="${PROJECTS[$i]// /}"  # Trim whitespace
        if [ $i -eq 0 ]; then
            PROJECT_YAML+="\"$PROJECT\""
        else
            PROJECT_YAML+=", \"$PROJECT\""
        fi
    done
    PROJECT_YAML+="]"

    # Ask about board IDs (optional but recommended)
    echo
    echo "Board IDs are optional but improve performance."
    read -p "Do you know your Jira board IDs? (y/n): " KNOW_BOARDS

    if [ "$KNOW_BOARDS" = "y" ]; then
        read -p "Enter board ID(s) (comma-separated, e.g., 123,456): " BOARD_IDS
        if [ -n "$BOARD_IDS" ]; then
            IFS=',' read -ra BOARDS <<< "$BOARD_IDS"
            BOARD_YAML="["
            for i in "${!BOARDS[@]}"; do
                BOARD="${BOARDS[$i]// /}"
                if [ $i -eq 0 ]; then
                    BOARD_YAML+="$BOARD"
                else
                    BOARD_YAML+=", $BOARD"
                fi
            done
            BOARD_YAML+="]"
        fi
    fi

    # Create config.yaml
    echo
    echo "Creating config.yaml..."

    cp "$PROJECT_DIR/config/config.example.yaml" "$CONFIG_FILE"

    # Update projects in config
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s/projects: \[.*\]/projects: $PROJECT_YAML/" "$CONFIG_FILE"
        if [ -n "$BOARD_YAML" ]; then
            sed -i '' "s/# board_ids: \[.*\]/board_ids: $BOARD_YAML/" "$CONFIG_FILE"
        fi
    else
        # Linux
        sed -i "s/projects: \[.*\]/projects: $PROJECT_YAML/" "$CONFIG_FILE"
        if [ -n "$BOARD_YAML" ]; then
            sed -i "s/# board_ids: \[.*\]/board_ids: $BOARD_YAML/" "$CONFIG_FILE"
        fi
    fi

    echo "✓ Created config.yaml at: $CONFIG_FILE"
    echo
fi

echo "=========================================="
echo "✓ Setup Complete!"
echo "=========================================="
echo
echo "Configuration files:"
echo "  .env:         $ENV_FILE"
echo "  config.yaml:  $CONFIG_FILE"
echo
echo "Next steps:"
echo "  1. Test Jira connection:"
echo "     python scripts/test_jira_connection.py"
echo
echo "  2. Extract metrics:"
echo "     python scripts/extract_metrics.py"
echo
echo "  3. View dashboard:"
echo "     cd dashboard && python -m http.server 8000"
echo "     Then open: http://localhost:8000"
echo
