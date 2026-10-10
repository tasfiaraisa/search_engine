Seekr
Description
In this project, we deploy a web application that uses Google OAuth2 login and session management. The application allows users to log in via Google, perform searches, and view their search history. We’re hosting the application on an AWS EC2 instance, accessible via our Elastic IP 18.233.193.248.

Prerequisites
Elastic IP (ours is 18.233.193.248) to allow consistent access to the app.


Setup Instructions
Step 1: Launch and Configure the EC2 Instance
Run ec2_setup.py to Launch an Instance:

In the backend folder, we can launch an EC2 instance by running ec2_setup.py.
To generate a new key pair, uncomment the create_key function in the script. This will create a key pair for SSH access, which we can download and use to connect.
Run the script ec2_setup.py to set up the instance.

Associate Elastic IP:
Once the instance is running, go to the AWS EC2 Dashboard.
Under Elastic IPs, either allocate a new Elastic IP or use an existing one.
Associate the Elastic IP (in our case, 18.233.193.248) with our newly created instance.

Update Security Group:
In the AWS EC2 Dashboard, configure the security group for the instance to allow inbound traffic on port 8080.
Edit the inbound rules to permit HTTP traffic on port 8080 from any IP (0.0.0.0/0).


Step 2: Connect to the EC2 Instance
SSH into the EC2 Instance:
Using the downloaded key pair file, SSH into the instance using the Elastic IP.
Step 3: Install Required Packages on the EC2 Instance
Update and Install Packages:
After connecting to the instance, update the package list and install necessary dependencies.
Install bottle, beaker, google-api-python-client, oauth2client, and httplib2 to support our application’s requirements.


Step 4: Transfer Project Files to the EC2 Instance
Transfer Files:
Copy all project files (including app.py, client_secret.json, static files, and templates) from our local system to the /home/ubuntu/project directory on the instance.


Step 5: Run the Application on EC2
Navigate to the Project Directory:
Go to /home/ubuntu/project on the EC2 instance.
Start the Application in the Background:
Use nohup to run app.py in the background, allowing it to keep running even if we close the SSH session.


Step 6: 
Open a browser and navigate to http://18.233.193.248:8080/ to use the application as if it’s running locally.


Step 7: Performance Testing
To test the performance of the application, we used several tools:

ApacheBench (ab): To test the number of requests our server can handle.

Example command: ab -n 1000 -c 20 http://18.233.193.248:8080/
iostat: To monitor disk I/O performance.

Example command: iostat -x 5
dstat: To monitor CPU, memory, and network usage.

Example command: dstat --cpu --mem --disk