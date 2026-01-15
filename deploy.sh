#!/bin/bash

# BinaApp Delivery System - Deployment Script
# Pushes changes to GitHub main branch to trigger Render deployment

set -e  # Exit on error

echo "🚀 BinaApp Delivery System - Deployment Script"
echo "================================================"
echo ""

# Check we're in the right directory
if [ ! -f "render.yaml" ]; then
    echo "❌ Error: render.yaml not found. Please run from binaapp directory."
    exit 1
fi

# Check we're on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "⚠️  Current branch: $CURRENT_BRANCH"
    echo "   Switching to main branch..."
    git checkout main
fi

# Show what will be pushed
echo "📋 Commits to be deployed:"
echo ""
git log --oneline origin/main..HEAD | head -10
echo ""

# Count unpushed commits
UNPUSHED=$(git log --oneline origin/main..HEAD | wc -l)
echo "📊 Total commits to push: $UNPUSHED"
echo ""

if [ "$UNPUSHED" -eq 0 ]; then
    echo "✅ Already up to date. Nothing to deploy."
    exit 0
fi

# Show what's being deployed
echo "🎯 New features being deployed:"
echo "   - Complete delivery system (10 tables)"
echo "   - 7 API endpoints (/v1/delivery/*)"
echo "   - Customer ordering widget"
echo "   - Order tracking system"
echo "   - Auto-generated order numbers"
echo ""

# Confirm deployment
read -p "🚀 Push to GitHub and trigger Render deployment? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "❌ Deployment cancelled."
    exit 1
fi

echo ""
echo "📤 Pushing to GitHub main branch..."
echo ""

# Push to GitHub
if git push origin main; then
    echo ""
    echo "✅ Successfully pushed to GitHub!"
    echo ""
    echo "🎯 Next steps:"
    echo "   1. Monitor Render deployment: https://dashboard.render.com"
    echo "   2. Check build logs for any errors"
    echo "   3. Wait for deployment to complete (~3-5 minutes)"
    echo "   4. Test endpoints when ready"
    echo ""
    echo "📊 Deployment verification:"
    echo "   Health check: https://binaapp-backend.onrender.com/health"
    echo "   API docs:     https://binaapp-backend.onrender.com/docs"
    echo "   Delivery API: https://binaapp-backend.onrender.com/v1/delivery/health"
    echo ""
    echo "🎉 Deployment initiated successfully!"
else
    echo ""
    echo "❌ Push failed!"
    echo ""
    echo "🔧 Troubleshooting:"
    echo "   1. Check your GitHub authentication"
    echo "   2. Verify you have push access to the repository"
    echo "   3. Try: git push origin main --force-with-lease"
    echo ""
    echo "📖 See RENDER_DEPLOYMENT.md for manual deployment steps"
    exit 1
fi
