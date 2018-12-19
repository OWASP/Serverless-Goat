## Introduction ##
Thank you for using OWASP ServerlessGoat!
​
This serverless application demonstrates common serverless security flaws as described in the Serverless Security Top 10 Weaknesses guide [https://github.com/puresec/sas-top-10](https://github.com/puresec/sas-top-10).  ​

ServerlessGoat was created for the following educational purposes:
* Teach developers & security practitioners about common serverless application layer risks and weaknesses 
* Educate on how serverless application layer weaknesses can be exploited
* Teach developers & security practitioners about serverless security best-practices  
​

You can find more information about WebGoat at: [https://www.owasp.org/index.php/OWASP_Serverless_Goat](https://www.owasp.org/index.php/OWASP_Serverless_Goat)

**​WARNING 1**: This application contains vulnerabilities. Use it only for training purposes.  
**WARNING 2**: This program is for educational purposes only. Do not attempt these techniques without authorization from application owners.  ​

**NOTE**: The application was developed in such way that should not put your AWS account at risk. The vulnerabilities that were introduced are contained within the boundaries of this specific application. Nevertheless, users are not encouraged to deploy the application in production environments.

​
## Deployment ##
ServerlessGoat is a simple AWS Lambda application, which serves as a MS-Word .doc file to plain text converter service. It receives a URL to a .doc file as input, and will return the text inside the document back to the API caller.
​
The application is packaged and published for deployment through the [AWS Serverless Application Repository](https://serverlessrepo.aws.amazon.com/applications/arn:aws:serverlessrepo:us-east-1:761130837472:applications~serverless-goat).
​
Steps for deployment:
1. Make sure you are logged into your AWS account
2. Click on the following link: [AWS Serverless Application Repository](https://serverlessrepo.aws.amazon.com/applications/arn:aws:serverlessrepo:us-east-1:761130837472:applications~serverless-goat)
3. Click 'Deploy'
4. Click 'Deploy' (again)
5. Wait until you see the message 'Your application has been deployed'
6. Click on 'View CloudFormation Stack'
7. Under 'Outputs' you will find the URL for the application (WebsiteURL)
​
## Cheat-Sheet ##

The full walkthrough of the lessons (under development) can be found in the [LESSONS.md](https://github.com/OWASP/Serverless-Goat/blob/master/LESSONS.md) file

The following security issues exist in the application:
​
* Event-data injection, leading to OS command injection (SAS-01)
  * Users can invoke the API with a `document_url` parameter value containing Linux OS commands. E.g. `; ls -LF`
* Improper exception handling and verbose error messages (SAS-10), leading to sensitive information disclosure
  * For example, invoking the API without the required parameter will return a verbose stack trace/exception
* Insecure Serverless Deployment Configuration (SAS-03)
  * Publicly open S3 bucket (its name can be discovered from the subdomain/prefix of the URL)
  * The parameter `document_url` is not defined as a 'required' parameter in API gateway and can be ommitted
* Over-privileged function permissions & roles, leading to data leakage of information stored in a DynamoDB table (SAS-04)
  * The function has CRUD permissions on the Dynamo table, which can be abused for reading sensitive data, or manipulating data
  * The function has FullAccess policy on the S3 bucket, leading to data tampering and data leakage, etc.
* Inadequate function monitoring and logging (SAS-05) - the application doesn't properly log application layer attacks and errors (can be demonstrated through CloudWatch/CloudTrail)
* Insecure 3rd Party Dependencies (SAS-06) - can be detected by scanning the project with an OSS scanning tool
  * The vulnerable package is `node-uuid` 
* Application layer Denial of Service (SAS-08), which can be easily demonstrated
  * An attacker may invoke the API recursively multiple times, essentially spawning enough instances to reach the function's reserved capacity limit (which is set to 5). For example:
    ```
    https://i92uw6vw73.execute-api.us-east-1.amazonaws.com/Prod/api/convert?document_url=https%3A%2F%2Fi92uw6vw73.execute-api.us-east-1.amazonaws.com%2FProd%2Fapi%2Fconvert%3Fdocument_url...
    ``` 
* An undisclosed *critical* issue, as a bonus! 

## Acknowledgements ##
ServerlessGoat was initially created and contributed to OWASP by Yuri Shapira & Ory Segal, [PureSec](https://www.puresec.io/).
​
