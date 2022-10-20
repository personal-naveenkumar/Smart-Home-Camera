const express = require("express");
const multer = require("multer");
const AWS = require("aws-sdk");
const { Consumer } = require("sqs-consumer");
const server = express();
const PORT = 3000;

// check if aws credentials are set
AWS.config.getCredentials(function (err) {
  if (err) {
    console.log(err.stack);
  }
});

// set region
AWS.config.update({ region: "us-east-1" });

// creating sqs service object
var sqs = new AWS.SQS({ apiVersion: "2012-11-05" });

// uploaded images are saved in the folder "/upload_images"
const upload = multer({ dest: __dirname + "/upload_images" });

server.use(express.static("public"));

// "myfile" is the key in the http payload
server.post("/upload-file",  upload.single("myfile"), function (request, response) {

    request.setTimeout(600000);
    
    if (request.file) {
      console.log(new Date().toJSON() + " === " + request.file.originalname + " Request received for file; size=" + request.file.size);
    } else {
      console.log("not a file");
    }

    var fs = require("fs");

    // send image as base-64 encoding to InputQ
    let imageAsBase64 = fs.readFileSync(
      __dirname + "/upload_images/" + request.file.filename,
      "base64"
    );

    const params = {
      //MessageBody: "Test sending message to sqs queue.",
      MessageBody: JSON.stringify({
        'img':imageAsBase64,
        'fileName':request.file.originalname.toString()
      }),
      // Required and must be unique for each message in FIFO queues.
      MessageDeduplicationId:
        request.file.originalname.toString() +
        Math.floor(Math.random() * 1000).toString(),
      MessageGroupId: "2", // Required for FIFO. Same group messages follow FIFO strictly
      QueueUrl: "https://sqs.us-east-1.amazonaws.com/600083409750/InputQ.fifo",
    };

    sqs.sendMessage(params, function (err, data) {
      if (err) {
        console.log(new Date().toJSON() + " === " + request.file.originalname + " Error sending file to queue", err);
      } else {
        console.log(new Date().toJSON() + " === " + request.file.originalname + " Success sending file to SQS queue; messageId=", data.MessageId);
      }
    });
    
    var intervalId = setInterval(function () {
      if (imagesLabelMap.has(request.file.originalname)) {
        clearInterval(intervalId);
        let imageLabel = imagesLabelMap.get(request.file.originalname);
        console.log(new Date().toJSON() + " === " + request.file.originalname + " Response returned for file; result=" + imageLabel);
        imagesLabelMap.delete((req = request.file.originalname));
        response.send(imageLabel);
      }
    }, 2000);
  }
);

server.get("/health", function (request, response) {
  console.log(new Date().toJSON() + " Health check");
  response.send("web server is alive.");
});


// receive image from OutputQ
let imagesLabelMap = new Map();

const queueReceiver = Consumer.create({
  queueUrl: "https://sqs.us-east-1.amazonaws.com/69993409750/OutputQ.fifo", // needs to be updated
  handleMessage: async (message) => {
    let sqsMessage = JSON.parse(message.Body);
    //console.log("queueReceiver handlemessage imagesLabelMap current size: " + imagesLabelMap.size + " " + new Date().toJSON());
    imagesLabelMap.set(sqsMessage.fileName, sqsMessage.result);
    console.log(new Date().toJSON() + " ======= " + sqsMessage.fileName + " Read by output queue receiver; result=" + sqsMessage.result);
  },
  sqs: new AWS.SQS(),
});

queueReceiver.on("error", (err) => {
  console.error(err.message);
});

queueReceiver.on("processing_error", (err) => {
  console.error(err.message);
});

queueReceiver.on("timeout_error", (err) => {
  console.error(err.message);
});

console.log("Output queue receiver is running");
queueReceiver.start();

// We need to configure node.js to listen on 0.0.0.0 so it will be able to accept connections on all the IPs of our machine
const hostname = "0.0.0.0";
server.listen(PORT, hostname, () => {
  console.log(`Server running at http://${hostname}:${PORT}/`);
});
