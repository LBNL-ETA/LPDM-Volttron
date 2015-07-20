#! /usr/bin/env python

'''
This script uploads a csv file to the smap historian, along with optional metadata.
'''

import uuid
import json
import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

def run_shell_cmd(cmd):
    from subprocess import Popen, PIPE    

    p = Popen(cmd, shell=True, stdout=PIPE, stderr=PIPE, close_fds=True)
    p.wait()    
    stdOut = p.stdout.read()
    stdErr = p.stderr.read()
    
    return stdOut, stdErr    

def check_curl_success(stdout, stderr):
    """
        need a way to check to see if the post was successful.  Failure returns a string that I am parsing
        to check for 3 digit numbers starting with 5 since that is the errors I was seeing.  Probably not sufficient
        for dealing with errors in a general sense
    """

    import re
    pattern = ".*\<title\>5\d\d.*"
    stdout_match = re.match(pattern, stdout.replace("\n", ""))
    stderr_match = re.match(pattern, stderr.replace("\n", ""))
    
    
    if stdout_match or stderr_match:
        return False
    return True
    

def get_everything_to_post_except_timeseries(source_name, path, obj_uuid, units="kW", additional_metadata = {}):
    """
        This function deals with handling all the metadata.  i.e. everything that isn't a (timestamp, value) pair.
        Since one of the fields is actually called "metadata" I am going to refer to the entire collection as headers for this
        function
    """
    
    headers = {}
    headers[path] = {}

    headers[path]["Metadata"] = {}
    if source_name:
        headers[path]["Metadata"]["SourceName"] = source_name
    
    if additional_metadata:
        for k,v in additional_metadata.iteritems():
            headers[path]["Metadata"][k] = v

    headers[path]["Properties"] = {}
    headers[path]["Properties"]["Timezone"] = "US/Pacific"
    headers[path]["Properties"]["ReadingType"] = "double"
    headers[path]["Properties"]["UnitofMeasure"] = units

    if obj_uuid:
        headers[path]["uuid"] = obj_uuid
    else:
        headers[path]["uuid"] = str(uuid.uuid4())


    return headers

def get_data_to_post(everything_except_timeseries_dict, path, timeseries):
    res = everything_except_timeseries_dict
    for ndx in xrange(len(timeseries)):
        timeseries[ndx][0] = int(timeseries[ndx][0])
    res[path]["Readings"] = timeseries
    
    return res

def create_JSON_file_to_post(infoToPost):
    with open("/tmp/data.json", 'w') as outfile:
        outfile.write(json.dumps(infoToPost))

def chunk_list(lst, num_elements_in_sublist):
    return [lst[i:i+num_elements_in_sublist] for i in range(0, len(lst), num_elements_in_sublist)]
    
            
def upload(readings, url, api_key, source_name, path, obj_uuid, units="kW", additional_metadata = {}, doRobustUpload=True):
    import time
    logger.debug("Starting smap_upload_csv.uploadFile path = " + path)
    logger.debug("Trying to upload:\nfirst_point:\t{d_start}\nlast_point:\t{d_end}".format(d_start = readings[0], d_end = readings[-1]))    
    to_smap_time = lambda x: 1000*time.mktime(x.timetuple())
    #try parsing to smap time.  If it fails assume the timestamps are already in the expect time (unix time in ms)
    try:
        to_smap_time(readings[0][0])
        readings = [[to_smap_time(i[0]), float(i[1])] for i in readings]
    except Exception as e:
        pass
    
    headers = get_everything_to_post_except_timeseries(source_name, path, obj_uuid, units, additional_metadata)
    create_JSON_file_to_post(get_data_to_post(headers, path, readings))

    if url[-1] == "/":
        url = url[:-1]

    curl_cmd = "curl -XPOST -d @%s -H \"Content-Type: application/json\" %s/backend/add/%s" % \
              ("/tmp/data.json", url, api_key)

    logger.debug("Running command: %s" % curl_cmd)
    stdout, stderr = run_shell_cmd(curl_cmd)
    logger.debug("stdout:\t{stdout}\nstderr:\t{stderr}".format(stdout = stdout, stderr = stderr))
    success = check_curl_success(stdout, stderr)
    
    if success or not doRobustUpload:
        logger.debug("Successfully uploaded data")
        return success
    
    logger.debug("Posting data to smap in one file failed.  Attempting to split the file into smaller pieces and post individually.")
    
    #if we are here than the upload failed.  Try breaking it into smaller chunks and post those with repetition in case of failure
    nPoints = 20000
    chunks = chunk_list(readings, nPoints)
    maxAttempts = 10    
    
    for chunk in chunks:
        logger.debug("Posting file with %i points to smap path %s." % (len(chunk), path))
        attempt = 1
        success = False
        while not success:        
            create_JSON_file_to_post(get_data_to_post(headers, path, chunk))
            stdout, stderr = run_shell_cmd(curl_cmd)
            success = check_curl_success(stdout, stderr)
            
            if not success:
                logger.debug("Posting file with %i points to smap failed.  Attempt: " % (len(chunk), attempt))                
                if attempt > maxAttempts:
                    logger.debug("Posting file with %i points to smap failed on all %i attempts.  Aborting." % (len(chunk), attempt))                    
                    return False
                else:
                    attempt += 1                            
        
    return True


