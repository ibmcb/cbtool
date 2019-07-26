#!/usr/bin/env node

/*
#/*******************************************************************************
# Copyright (c) 2019 DigitalOcean

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#/*******************************************************************************
*/

// CREDIT: Modified from: https://www.freecodecamp.org/news/how-we-fine-tuned-haproxy-to-achieve-2-000-000-concurrent-ssl-connections-d017e61a4d27/

var http = require('http');
var argv = process.argv;
var port = 80;

if (argv.length > 2) {
        port = parseInt(argv[2]);
}

console.log("Requested port: " + port);

function randomIntInc (low, high){
        return Math.floor(Math.random() * (high - low + 1) + low);
}

function sendResponse(res, httphang, sleep, response_size) {
        //rsize = randomIntInc(1, response_size);
        rsize = response_size;
        for(x = 0; x < rsize; x++) {
            res.write('x');
        }
        res.write('\n');
        if(!httphang) {
            res.end();
        }
}
function server(req, res) {
        headers = req.headers;
        old_sleep = parseInt(headers["sleep"]);
        response_size = parseInt(headers["size"]);
        httphang = headers["httphang"] || 0;
        //sleep = randomIntInc(0, old_sleep+1);
        sleep = old_sleep;
        res.writeHead(200);
        setTimeout(sendResponse, sleep, res, httphang, old_sleep, response_size - 1);
}

var server = http.createServer(server);

server.timeout = 3600000;
server.listen(port);
