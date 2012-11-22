/*******************************************************************************
 Copyright (c) 2012 IBM Corp.

 Licensed under the Apache License, Version 2.0 (the "License");
 you may not use this file except in compliance with the License.
 You may obtain a copy of the License at

     http://www.apache.org/licenses/LICENSE-2.0

 Unless required by applicable law or agreed to in writing, software
 distributed under the License is distributed on an "AS IS" BASIS,
 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 See the License for the specific language governing permissions and
 limitations under the License.
*******************************************************************************/
  debugger;
var bootdest = "";
//var bootdest = window.location.href.match(/[^/]*\/([^/]*)/g)[2];
var last_data = '';
var first_time = true; 
var debug = false;
//var debug = true;
var unavailable = "CloudBench is unreachable. Will try again later...";
var prmstr = window.location.search.substr(1);
var prmarr = prmstr.split ("&");
var params = {};
var heromsg = "<div class='hero-unit' style='padding: 5px'>";
for ( var i = 0; i < prmarr.length; i++) {
    var tmparr = prmarr[i].split("=");
    params[tmparr[0]] = tmparr[1];
}
var active = "app";
var liststate = "all";
if ("object" in params)
    active = params["object"];
    
if ("liststate" in params)
    liststate = params["liststate"];

  var do_refresh = false;
  var secs = 20;
  var failcount = 0;
  var newRefresh = 0;
  var finish = false;
  function populateRefreshChoices() {
      e = document.getElementById('changerefresh');
      e.options.length=0;
      for(x = 0; x < (parseInt(secs) + 60); x++) {
          e.options[x] = new Option(x, x);
          if (x == secs)
              e.options.selectedIndex = x;
      }    
  }
  function doNewRefresh() {
      e = document.getElementById('changerefresh');
      newRefresh = e.options[e.selectedIndex].value;
      secs = newRefresh;
      populateRefreshChoices();
  }
  function CountBack(id, barid, left) {
    if(do_refresh) {
        if(left >= 0) {
            newSecs = left - 1;
            if(newRefresh) {
              newSecs = newRefresh;
              newRefresh = 0;
            }
            if(id != false && id != 'false')
                document.getElementById(id).innerHTML = 'Next Check: ' + left;
            if(left != 0 && barid != false && barid != 'false')
                document.getElementById(barid).style.width = ((secs - left) / secs) * 100 + "%";
            setTimeout("CountBack('" + id + "', '" + barid + "', " + newSecs + ");", 990);
        } else {
          if(finish != false) 
              finish();
        }
    } else {
        if(id != false && id != 'false')
            document.getElementById(id).innerHTML = '';
    }
  }
  function go(id, url, getSpecificContent, error, writeSubcontent, callback, write){
      jQuery.ajax({
        url: url,
        type: "GET",
        dataType: "html",
        error: function (XMLHttpRequest, ajaxOptions, thrownError) {
              if(XMLHttpRequest.statusText == 'error')
                  $(id).html("<div class='hero-unit' style='padding: 5px'><h4><img src='data:image/gif;base64,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' width='20px'>&nbsp;&nbsp;" + error + "</h4></div>");
             if(callback != false)
               callback('error');
        },
        success: function (response) {
            var data = "none";
            if(getSpecificContent != '') {
                data = $(response).find(getSpecificContent).html();
                if(write) {
                    if(writeSubcontent)
                        $(id).html(data);
                    else
                        $(id).html(response);
                }
            } else {
                if(write)
                    $(id).html(response);
                data = response;
            }
            if(callback != false)
               callback(data);
        }
      });
  }
  function resetMonitor(data) {
      if(data != 'error') {
          htmlobj = $(data);
          $("#summary").html(htmlobj.find("#monitorsummary"));
          htmlobj = $(data);
          $("#taball").html(htmlobj.find("#monitordata"));
          htmlobj = $(data);
          var choices = new Array('p', 'h', 's', 'a');
          var x = 0;
          for(x = 0; x <=3 ; x++) {
              y = choices[x];
              htmlobj = $(data);
              result = htmlobj.find("#monitor" + y);
              if((result.html() + "") == "null")
                  $("#tab" + y).html("<h3>This performance category is not configured. Click 'Options' to activate.</h3>");
              else
                  $("#tab" + y).html(result);
          }
      } else {
          $("#summary").html("<h4 style='color: red'>CloudBench is unavailable. Will try again later...</h4>");
      }
      finish = checkMonitor;
      do_refresh = true;
      CountBack('count', 'countbar', secs);
  }
  function startRefresh() {
      checkMonitor();
      $('#refreshButton').button('disable');
      $('#refreshButton').on('click', stopRefresh);
  }
  function stopRefresh() {
      do_refresh = false;
      $('#refreshButton').button('enable');
      $('#refreshButton').on('click', startRefresh);
  }

function poll(s, finisher) {
        secs = s;
        do_refresh = true;
        finish = finisher;
        if(debug)
            CountBack('pendingcount', false, s);
        else
            CountBack(false, false, s);
}
function check_nodraw() {
   go('#pendingtest', bootdest + '/provision?pending=1&object=' + active, '#pendingresult', unavailable, true, pending_callback, false);
}
function pending_callback(data) {
        if (!debug && last_data == '')
            $('#pendingcount2').html('');
        if(data == 'unchanged') {
            if(debug)
                $('#pendingcount2').html('result: unchanged ' + last_data);
            if(last_data == 'No Pending Objects') {
		go('#allstate', bootdest + '/provision?allstate=1&liststate=' + liststate + '&object=' + active, '#allstate', unavailable, true, false, true);
                poll(30, check_nodraw);
            } else {
                poll(3, check_nodraw);
            }
        } else if(data == 'error' || data == 'none' || data == 'No Pending Objects') {
            last_data = '';
            $('#pendingtest').html('');
            $('#pendingstatus').html('');
            if("operation" in params) {
               $('#pendingtest').html(heromsg + "<h4>&nbsp;&nbsp;Request(s) Complete.</h4></div>");
            }
            if(data == 'error') {
                first_time = true;
                poll(1, check_pending);
            } else if (data == 'No Pending Objects') {
		go('#allstate', bootdest + '/provision?allstate=1&liststate=' + liststate + '&object=' + active, '#allstate', unavailable, true, false, true);
                last_data = data;
                poll(30, check_pending);
	    } else {
                last_data = data;
                poll(30, check_pending);
            }
            if(debug)
                $('#pendingcount2').html('result: ' + data);
        } else {
            last_data = data;
            $('#pendingtest').html(last_data);
            if(debug)
                $('#pendingcount2').html('result: new pending data');
            poll(3, check_pending);
        }
}
function check_pending() {
    if(first_time) {
        first_time = false;
        go('#pendingtest', bootdest + '/provision?force=1&pending=1&object=' + active, '#pendingresult', unavailable, true, pending_callback, false);
    } else {
        go('#pendingtest', bootdest + '/provision?pending=1&object=' + active, '#pendingresult', unavailable, true, pending_callback, false);
        go('#allstate', bootdest + '/provision?allstate=1&liststate=' + liststate + '&object=' + active, '#allstate', unavailable, true, false, true);
    }
}
function checkMonitor() {
	var error = "CloudBench is unreachable, will try again later...";
	$('#count').html("Polling...");
	go('#monitordata', bootdest + '/monitordata', '', error, false, resetMonitor, false);
}    

function make_child(node) {
     var contents = "<" + node.nodeName;
    for(var y = 0; y < node.attributes.length; y++) {
        contents += " " + node.attributes[y].name + "='" + node.attributes[y].value + "'";
    }
     if (node.childElementCount == 0)
         contents += "/";
     contents += ">\\n";
     for(var x = 0; x < node.childElementCount; x++)
         contents += make_child(node.childNodes[x]);
     if (node.childElementCount > 0)
         contents += "</" + node.nodeName + ">\\n";
    return contents;
}

  /* Used in click events. We want to know if the parent of a click event
     object is the body itself or an internal div. This allows us to
     make sure we don't hide the content when we click on the content itself.
     */
  function findParentNode(parentName, childObj, stopName) {
	    var testObj = childObj.parentNode;
	    var count = 1;
	    if("getAttribute" in testObj) {
		    while(testObj.getAttribute('id') != parentName && testObj.getAttribute('id') != stopName) {
	//	        alert('My id  is ' + testObj.getAttribute('id') + '. Let\'s try moving up one level to see what we get.');
			testObj = testObj.parentNode;
			count++;
		    }
	    } else {
		return false;
	    }
	    // now you have the object you are looking for - do something with it
//	    alert('Finally found ' + testObj.getAttribute('id') + ' after going up ' + count + ' level(s) through the DOM tree');
	    return (testObj.getAttribute('id') == stopName) ? false : true;
  }
