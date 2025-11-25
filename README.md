# Infrastructure Architecture
This application requires a specific network setup on AWS:
- **VPC**: Create a VPC with **2 Public Subnets** and **2 Private Subnets**.
- **Database**: The RDS instance must be deployed in the **Private Subnets** for security.
- **Deployment**: The application is deployed using an **Auto Scaling Group (ASG)**.

# CI/CD Development
## Install Dependencies
`pip install -r requirements.txt`

## Setting Environments
AWS_REGION=us-east-1<br/>
S3_BUCKET_NAME=your bucket name<br/>
API_GATEWAY_URL=your API Gateway URL<br/>


## Running Apps
python app.py