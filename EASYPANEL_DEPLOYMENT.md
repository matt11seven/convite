# EasyPanel Deployment Guide for Convites Application

This guide will help you deploy the Convites application to EasyPanel using Docker.

## Prerequisites

- EasyPanel installed and running
- Git repository with your application code
- MongoDB instance (can be deployed in EasyPanel or external)
- Backblaze B2 account configured (required for file storage)

## Deployment Steps

### 1. Prepare Environment Variables

Create a `.env` file in EasyPanel with the following environment variables:

```
MONGO_URL=mongodb://mongodb:27017/
B2_ENDPOINT=your_b2_endpoint
B2_ACCESS_KEY_ID=your_b2_access_key_id
B2_SECRET_ACCESS_KEY=your_b2_secret_access_key
B2_BUCKET_NAME=your_b2_bucket_name
B2_REGION=your_b2_region
JWT_SECRET_KEY=generate_a_secure_random_key
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24
MAX_FILE_SIZE=5242880
ALLOWED_EXTENSIONS=jpg,jpeg,png,gif,webp
RATE_LIMIT_PER_MINUTE=30
ADMIN_EMAIL=your_admin_email
ADMIN_PASSWORD=your_secure_admin_password
```

### 2. Create a New Project in EasyPanel

1. Log in to your EasyPanel dashboard
2. Click "New Project"
3. Choose "Docker" as the project type
4. Configure the following settings:
   - Project name: `convites-app`
   - Image: Use repository (point to your Git repository)
   - Port: `8001`
   - Environment variables: Import from the `.env` file created earlier

### 3. Configure Persistent Storage

Add the following persistent volumes in the EasyPanel project settings:

1. `/app/generated_images`: For storing generated invite images
2. `/data/db`: For MongoDB data if using the internal MongoDB service

### 4. Deploy MongoDB (if not using external MongoDB)

If you don't have an external MongoDB instance:

1. Create another project in EasyPanel
2. Choose "MongoDB" template
3. Name it `convites-mongodb`
4. Set the port to `27017`
5. Configure a persistent volume for `/data/db`
6. Update the `MONGO_URL` in your main application's environment variables to point to this MongoDB instance

### 5. Configure Network

Create a network in EasyPanel and add both the application and MongoDB services to it.

### 6. Build and Deploy

1. Click "Deploy" in the EasyPanel dashboard
2. EasyPanel will use the Dockerfile in your repository to build and deploy the application
3. Wait for the build process to complete

### 7. Access Your Application

Once deployed, your application will be available at:

```
http://your-easypanel-domain:8001
```

### 8. Troubleshooting

If you encounter any issues:

1. Check the application logs in EasyPanel dashboard
2. Verify that all environment variables are correctly set
3. Ensure MongoDB is accessible from the application
4. Check that Backblaze B2 credentials are valid

## Maintenance

### Updating Your Application

To update your application:

1. Push changes to your Git repository
2. In the EasyPanel dashboard, click "Rebuild" for your application

### Backing Up Data

Regularly backup your MongoDB data and generated images.

## Security Considerations

1. Always use secure passwords and JWT secrets
2. Use HTTPS when deploying to production
3. Consider using EasyPanel's built-in SSL/TLS support
4. Restrict access to the admin interface

---

For more information about EasyPanel configuration, please refer to the [official EasyPanel documentation](https://easypanel.io/docs).
