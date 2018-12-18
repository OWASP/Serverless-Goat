const fs = require('fs');
exports.handler = async (event) => {

  return {
    statusCode: 200,
    headers: {
      'Content-Type': 'text/html'
    },
    body: fs.readFileSync('index.html').toString()
  };
};
