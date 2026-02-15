# Quick Start: CI/CD Setup

Follow these steps to get GitHub Actions CI/CD working for your Virtual Family Bank project.

## Prerequisites

✅ GitHub repository created
✅ AWS account with admin access
✅ AWS CLI configured locally

## Step 1: Create IAM User for GitHub Actions (5 minutes)

1. **Create IAM User**:
   ```bash
   aws iam create-user --user-name github-actions-family-bank
   ```

2. **Attach Policies**:
   ```bash
   # Create custom policy file
   cat > github-actions-policy.json << 'EOF'
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Effect": "Allow",
         "Action": [
           "cloudformation:*",
           "s3:*",
           "lambda:*",
           "apigateway:*",
           "dynamodb:*",
           "cognito-idp:*",
           "events:*",
           "iam:GetRole",
           "iam:CreateRole",
           "iam:DeleteRole",
           "iam:PutRolePolicy",
           "iam:AttachRolePolicy",
           "iam:DetachRolePolicy",
           "iam:DeleteRolePolicy",
           "iam:PassRole",
           "logs:*"
         ],
         "Resource": "*"
       }
     ]
   }
   EOF

   # Create policy
   aws iam create-policy \
     --policy-name GitHubActionsFamilyBank \
     --policy-document file://github-actions-policy.json

   # Attach policy to user (replace with your account ID)
   aws iam attach-user-policy \
     --user-name github-actions-family-bank \
     --policy-arn arn:aws:iam::YOUR_ACCOUNT_ID:policy/GitHubActionsFamilyBank
   ```

3. **Create Access Keys**:
   ```bash
   aws iam create-access-key --user-name github-actions-family-bank
   ```

   **Save the output!** You'll need:
   - `AccessKeyId`
   - `SecretAccessKey`

## Step 2: Configure GitHub Secrets (2 minutes)

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret** and add:

   **Required**:
   ```
   Name: AWS_ACCESS_KEY_ID
   Value: <AccessKeyId from Step 1>

   Name: AWS_SECRET_ACCESS_KEY
   Value: <SecretAccessKey from Step 1>
   ```

   **Optional** (for Google OAuth):
   ```
   Name: GOOGLE_CLIENT_ID
   Value: <Your Google OAuth Client ID>

   Name: GOOGLE_CLIENT_SECRET
   Value: <Your Google OAuth Client Secret>
   ```

   **Optional** (for frontend S3 hosting):
   ```
   Name: FRONTEND_S3_BUCKET
   Value: family-bank-frontend-dev

   Name: CLOUDFRONT_DISTRIBUTION_ID
   Value: <Your CloudFront distribution ID>
   ```

## Step 3: Test CI (1 minute)

1. Push any code to your repository:
   ```bash
   git add .
   git commit -m "test: trigger CI"
   git push
   ```

2. Go to GitHub → **Actions** tab
3. You should see "CI - Test & Lint" workflow running
4. Wait for it to complete (2-5 minutes)

## Step 4: First Deployment (10 minutes)

1. **Create S3 Bucket for SAM Artifacts**:
   ```bash
   aws s3 mb s3://family-bank-sam-artifacts-$(aws sts get-caller-identity --query Account --output text)
   ```

2. **Deploy Manually First Time**:
   ```bash
   cd backend
   sam build
   sam deploy --guided

   # Follow prompts:
   # - Stack Name: family-bank-dev
   # - AWS Region: us-east-1
   # - Confirm changes: Y
   # - Allow SAM CLI IAM role creation: Y
   # - Save arguments to config file: Y
   # - Config file: samconfig.toml
   # - Config environment: default
   ```

3. **Save Stack Outputs**:
   ```bash
   aws cloudformation describe-stacks \
     --stack-name family-bank-dev \
     --query 'Stacks[0].Outputs' \
     --output table
   ```

   Copy these values - you'll need them for the frontend!

4. **Test Automated Deployment**:
   ```bash
   git add backend/samconfig.toml
   git commit -m "feat: add SAM configuration"
   git push origin main
   ```

   This will trigger automatic deployment to dev!

## Step 5: Configure Frontend Environment (2 minutes)

1. Create `frontend/.env` with values from Step 4:
   ```env
   VITE_API_ENDPOINT=https://xxxxx.execute-api.us-east-1.amazonaws.com/dev
   VITE_AWS_REGION=us-east-1
   VITE_USER_POOL_ID=us-east-1_xxxxxxxxx
   VITE_USER_POOL_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxxxx
   VITE_COGNITO_DOMAIN=https://familybank-dev-xxxxx.auth.us-east-1.amazoncognito.com
   ```

2. **Don't commit `.env`!** It's in `.gitignore`

3. Test locally:
   ```bash
   cd frontend
   npm install
   npm run dev
   ```

## Step 6: (Optional) Set Up Frontend Hosting (10 minutes)

### Option A: S3 + CloudFront

1. **Create S3 Bucket**:
   ```bash
   aws s3 mb s3://family-bank-frontend-dev

   aws s3 website s3://family-bank-frontend-dev \
     --index-document index.html \
     --error-document index.html
   ```

2. **Create Bucket Policy**:
   ```bash
   cat > bucket-policy.json << EOF
   {
     "Version": "2012-10-17",
     "Statement": [
       {
         "Sid": "PublicReadGetObject",
         "Effect": "Allow",
         "Principal": "*",
         "Action": "s3:GetObject",
         "Resource": "arn:aws:s3:::family-bank-frontend-dev/*"
       }
     ]
   }
   EOF

   aws s3api put-bucket-policy \
     --bucket family-bank-frontend-dev \
     --policy file://bucket-policy.json
   ```

3. **Add Secret to GitHub**:
   - Name: `FRONTEND_S3_BUCKET`
   - Value: `family-bank-frontend-dev`

### Option B: Amplify Hosting

1. Go to AWS Amplify Console
2. Click **New app** → **Host web app**
3. Connect GitHub repository
4. Amplify will auto-detect Vite
5. Set environment variables in Amplify Console

### Option C: Vercel/Netlify

1. Connect repository to Vercel/Netlify
2. Set environment variables in their dashboard
3. Deploy!

## Verification Checklist

After setup, verify:

- [ ] CI workflow runs on push (GitHub Actions tab)
- [ ] Backend tests pass
- [ ] Frontend builds successfully
- [ ] SAM template validates
- [ ] Backend deploys to AWS on main branch merge
- [ ] Can access API Gateway endpoint
- [ ] Cognito User Pool exists
- [ ] Frontend builds with correct environment variables

## Test the Full Pipeline

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/test-cicd
   ```

2. **Make a small change**:
   ```bash
   echo "# Test" >> README.md
   git add README.md
   git commit -m "test: verify CI/CD pipeline"
   git push origin feature/test-cicd
   ```

3. **Create Pull Request** on GitHub

4. **Check PR Checks**:
   - CI should run automatically
   - PR checklist comment should appear
   - Size check should pass

5. **Merge PR**:
   - Merge to main
   - Deployment should trigger automatically
   - Check Actions tab for progress

6. **Verify Deployment**:
   ```bash
   # Get API endpoint
   API=$(aws cloudformation describe-stacks \
     --stack-name family-bank-dev \
     --query 'Stacks[0].Outputs[?OutputKey==`ApiEndpoint`].OutputValue' \
     --output text)

   # Test (should return 401 - auth required)
   curl -v $API/user
   ```

## Common Issues

### Issue: "AWS credentials not found"
**Fix**: Double-check secrets are named exactly:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

### Issue: "SAM deploy failed - bucket not found"
**Fix**: Run first deployment manually with `sam deploy --guided`

### Issue: "Frontend build fails"
**Fix**: Workflow uses dummy env vars for build. That's normal for CI.

### Issue: "Permission denied" errors
**Fix**: IAM user needs more permissions. Check CloudFormation console for specific error.

## Next Steps

Once CI/CD is working:

1. **Set up staging/prod environments**:
   - Add environment protection rules
   - Create separate Cognito User Pools
   - Use different AWS regions (optional)

2. **Add notifications**:
   - Slack webhooks
   - Email notifications
   - Discord/Teams integrations

3. **Enhance workflows**:
   - Add integration tests
   - Add E2E tests
   - Add performance tests
   - Add security scanning

## Getting Help

If you get stuck:

1. Check workflow logs in GitHub Actions
2. Review AWS CloudFormation console
3. Check CloudWatch logs for Lambda errors
4. See main documentation: `.github/workflows/README.md`

## Success! 🎉

You now have:
- ✅ Automated testing on every push
- ✅ Automated deployment to dev on merge
- ✅ PR checks and validation
- ✅ Manual deployment to staging/prod

Your pipeline is ready! Happy coding! 🚀
