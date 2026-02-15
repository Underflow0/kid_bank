# GitHub Actions CI/CD Workflows

This directory contains GitHub Actions workflows for automated testing, linting, and deployment of the Virtual Family Bank application.

## Workflows Overview

### 1. CI - Test & Lint (`ci.yml`)

**Triggers**: Push to main/master/develop, Pull Requests

**Jobs**:
- **Backend Tests**: Runs Python linting (flake8, black), type checking (mypy), and unit tests with coverage
- **Frontend Tests**: Runs ESLint, TypeScript checking, and builds the frontend
- **SAM Validation**: Validates SAM template syntax and builds the backend
- **Security Scan**: Runs Trivy vulnerability scanner
- **Summary**: Aggregates results from all jobs

**What it tests**:
- ✅ Python code quality (flake8, black)
- ✅ TypeScript code quality (ESLint)
- ✅ Unit test coverage (pytest)
- ✅ Frontend build success
- ✅ SAM template validity
- ✅ Security vulnerabilities

### 2. CD - Deploy (`deploy.yml`)

**Triggers**:
- Automatic: Push to main/master branch
- Manual: workflow_dispatch with environment selection

**Jobs**:
- **Deploy Backend**: Builds and deploys backend using SAM to AWS
- **Deploy Frontend**: Builds frontend with environment variables and deploys to S3 (optional)
- **Notify**: Posts deployment summary

**Environments**:
- `dev` - Development environment
- `staging` - Staging environment
- `prod` - Production environment

### 3. Pull Request Checks (`pr.yml`)

**Triggers**: Pull request opened, synchronized, reopened

**Jobs**:
- **PR Validation**: Checks PR title, changelog, breaking changes
- **Size Check**: Analyzes PR size and provides feedback
- **Dependency Review**: Scans for vulnerable dependencies

## Setup Instructions

### Required Secrets

Set these in GitHub repository settings → Secrets and variables → Actions:

#### AWS Credentials (Required for Deployment)
```
AWS_ACCESS_KEY_ID         - AWS access key for deployment
AWS_SECRET_ACCESS_KEY     - AWS secret key for deployment
```

#### Google OAuth (Optional - for Cognito Google login)
```
GOOGLE_CLIENT_ID          - Google OAuth Client ID
GOOGLE_CLIENT_SECRET      - Google OAuth Client Secret
```

#### Frontend Hosting (Optional - for S3 deployment)
```
FRONTEND_S3_BUCKET              - S3 bucket name for frontend hosting
CLOUDFRONT_DISTRIBUTION_ID      - CloudFront distribution ID (optional)
```

### Setup Steps

1. **Configure AWS Credentials**

   Create an IAM user with these permissions:
   - CloudFormation (full access)
   - S3 (full access for SAM artifacts)
   - Lambda (full access)
   - API Gateway (full access)
   - DynamoDB (full access)
   - Cognito (full access)
   - IAM (limited: CreateRole, AttachRolePolicy, etc.)
   - EventBridge (full access)

   Add credentials to GitHub secrets.

2. **Configure SAM Deployment**

   Ensure `backend/samconfig.toml` has configuration for all environments:
   ```toml
   [dev]
   [dev.deploy.parameters]
   stack_name = "family-bank-dev"
   region = "us-east-1"

   [staging]
   [staging.deploy.parameters]
   stack_name = "family-bank-staging"
   region = "us-east-1"

   [prod]
   [prod.deploy.parameters]
   stack_name = "family-bank-prod"
   region = "us-east-1"
   ```

3. **Configure Frontend Hosting (Optional)**

   To deploy frontend to S3:

   a. Create S3 bucket:
   ```bash
   aws s3 mb s3://family-bank-frontend-dev
   aws s3 website s3://family-bank-frontend-dev \
     --index-document index.html \
     --error-document index.html
   ```

   b. Create CloudFront distribution (optional for HTTPS)

   c. Add bucket name to GitHub secrets:
   ```
   FRONTEND_S3_BUCKET=family-bank-frontend-dev
   CLOUDFRONT_DISTRIBUTION_ID=E1234567890ABC
   ```

4. **Enable GitHub Actions**

   GitHub Actions should be enabled by default. Check:
   - Repository → Settings → Actions → General
   - Ensure "Allow all actions and reusable workflows" is selected

5. **Set up Environments (Optional)**

   For deployment protection:
   - Repository → Settings → Environments
   - Create environments: `dev`, `staging`, `prod`
   - Add protection rules for `prod`:
     - ✅ Required reviewers
     - ✅ Wait timer
     - ✅ Environment secrets

## Using the Workflows

### Running CI (Automatic)

CI runs automatically on:
- Every push to main/master/develop branches
- Every pull request

No manual action needed!

### Deploying to Dev (Automatic)

Push to main/master branch:
```bash
git push origin main
```

This automatically deploys to the `dev` environment.

### Deploying to Staging/Prod (Manual)

1. Go to GitHub → Actions → CD - Deploy
2. Click "Run workflow"
3. Select branch and environment
4. Click "Run workflow"

### Viewing Results

**CI Results**:
- Pull Requests: Check appears on PR page
- Commits: Check mark/X on commit in GitHub

**Deployment Results**:
- Actions tab → CD - Deploy → Latest run
- Check the "Summary" for deployment outputs
- Stack outputs (API URL, Cognito IDs) shown in summary

## Workflow Behavior

### On Pull Request
1. Runs all CI checks
2. Adds PR checklist comment
3. Checks PR size
4. Labels PR based on changed files
5. Reviews dependencies
6. **Does not deploy**

### On Merge to Main
1. Runs all CI checks
2. **Deploys backend to dev**
3. **Deploys frontend to dev**
4. Posts deployment summary
5. Uploads artifacts

### Manual Deployment
1. Select environment
2. Runs CI checks first
3. Deploys backend to selected environment
4. Deploys frontend to selected environment
5. Posts deployment summary

## Troubleshooting

### CI Failing

**Backend tests fail**:
- Check test logs in Actions
- Run tests locally: `cd backend && pytest tests/unit/`
- Ensure PYTHONPATH is set: `export PYTHONPATH=backend/src`

**Frontend build fails**:
- Check for TypeScript errors
- Run locally: `cd frontend && npm run build`
- Ensure all dependencies installed

**SAM validation fails**:
- Check `backend/template.yaml` syntax
- Run locally: `sam validate --lint`

### Deployment Failing

**AWS credentials error**:
- Verify `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` are set
- Check IAM user has required permissions

**SAM deploy fails**:
- Check CloudFormation console for stack errors
- Review SAM CLI output in Actions logs
- Ensure S3 bucket exists for SAM artifacts

**Frontend deploy fails**:
- Verify `FRONTEND_S3_BUCKET` secret is set
- Check S3 bucket exists and is accessible
- Ensure bucket policy allows PutObject

### Secrets Not Found

Secrets must be set at the repository level:
1. Repository → Settings
2. Secrets and variables → Actions
3. New repository secret

Don't set secrets in workflow files (they'll be exposed!).

## Customization

### Change Python/Node Versions

Edit workflow env variables:
```yaml
env:
  PYTHON_VERSION: '3.12'
  NODE_VERSION: '18'
```

### Add More Tests

Add steps to `ci.yml`:
```yaml
- name: Run integration tests
  run: pytest tests/integration/
```

### Change Deployment Regions

Edit `backend/samconfig.toml`:
```toml
[prod.deploy.parameters]
region = "us-west-2"
```

### Add Notifications

Add notification step to `deploy.yml`:
```yaml
- name: Notify Slack
  uses: slackapi/slack-github-action@v1
  with:
    webhook: ${{ secrets.SLACK_WEBHOOK }}
    payload: |
      {
        "text": "Deployment completed!"
      }
```

## Cost Considerations

**GitHub Actions Usage**:
- **Free tier**: 2,000 minutes/month for private repos
- **Public repos**: Unlimited free minutes
- This project uses ~5-10 minutes per workflow run

**AWS Resources**:
- CloudFormation: Free
- Lambda: Pay per invocation (free tier: 1M requests/month)
- S3: Pay per storage (~$0.023/GB/month)
- API Gateway: Pay per request (free tier: 1M requests/month)

Estimate: $5-10/month for dev environment with light usage.

## Security Best Practices

✅ **Never commit secrets** - Always use GitHub Secrets
✅ **Use environment protection** - Require approval for prod
✅ **Rotate credentials regularly** - Update AWS keys periodically
✅ **Limit IAM permissions** - Principle of least privilege
✅ **Enable MFA** - For AWS root and IAM users
✅ **Review dependency alerts** - Check Dependabot PRs
✅ **Scan for vulnerabilities** - Trivy runs automatically

## Monitoring Deployments

**CloudWatch Logs**:
```bash
aws logs tail /aws/lambda/family-bank-dev-GetUserFunction --follow
```

**Stack Status**:
```bash
aws cloudformation describe-stacks --stack-name family-bank-dev
```

**API Health Check**:
```bash
ENDPOINT=$(aws cloudformation describe-stacks \
  --stack-name family-bank-dev \
  --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
  --output text)
curl $ENDPOINT/user
```

## Support

For issues with workflows:
1. Check Actions logs for error details
2. Review this documentation
3. Check AWS CloudFormation console
4. Open an issue in the repository

## Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [AWS SAM CLI Reference](https://docs.aws.amazon.com/serverless-application-model/latest/developerguide/serverless-sam-cli-command-reference.html)
- [GitHub Environments](https://docs.github.com/en/actions/deployment/targeting-different-environments/using-environments-for-deployment)
