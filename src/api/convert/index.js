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

exports.handler = async (event) => {
  try {
    await log(event);

    let documentUrl = event.queryStringParameters.document_url;

    let txt = child_process.execSync(`curl --silent -L ${documentUrl} | /lib64/ld-linux-x86-64.so.2 ./bin/catdoc -`).toString();

    // Lambda response max size is 6MB. The workaround is to upload result to S3 and redirect user to the file.
    let key = uuid.v4();
    let s3 = new AWS.S3();
    await s3.putObject({
      Bucket: process.env.BUCKET_NAME,
      Key: key,
      Body: txt,
      ContentType: 'text/html',
      ACL: 'public-read'
    }).promise();

    return {
      statusCode: 302,
      headers: {
        "Location": `${process.env.BUCKET_URL}/${key}`
      }
    };
  }
  catch (err) {
    return {
      statusCode: 500,
      body: err.stack
    };
  }
};
