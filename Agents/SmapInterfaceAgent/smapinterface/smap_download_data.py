#! /usr/bin/env python


'''This is a script for downloading data from a sMAP database.

'''
from smap.archiver.client import SmapClient
from datetime import datetime, timedelta


import logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def get_stream_UUIDs_and_metadata(smap, streamName, source_name = None):
    from uuid import uuid1
    c = SmapClient(smap + "backend", timeout = 300)
    
    query = "Path = '{path}'".format(path = streamName)
    
    if source_name:
        query = query + "and Metadata/SourceName = '{source_name}'".format(source_name = source_name)
    
    tags = c.tags(query)
    
    res = {}
    
    for t in tags:
        res[t['uuid']] = t        
        
    return res

def download_latest_point(smap_root, stream_path, stream_uuids = None, source_name = None):
    import time
    
    logger.debug("starting download_latest_point.\nsmap_root = {smap_root}\nstream_path = {stream_path}\nuuids = {uuids}\nsource = {source}".format(smap_root = smap_root, stream_path = stream_path, uuids = stream_uuids, source = source_name))

    newest_ts = None
    newest_val = None
    newest_uuid = None
    timezone_of_newest_point = None

    try:
        c = SmapClient(smap_root + "backend")
        
        stream_uuids_and_metadata = get_stream_UUIDs_and_metadata(smap_root, stream_path, source_name)        
        if (not stream_uuids):            
            stream_uuids = stream_uuids_and_metadata.keys() 

        logger.debug("uuids: {uuids})".format(uuids = stream_uuids))
#NOTE:  Both SmapClient.prev and SmapClient.latest are broken in the release I am using.  I had to patch smap by changing the prev call in 
#/smap/archiver/client.py to look like prev(self, where, ref, limit=1, streamlimit=10):
        
        for uuid in stream_uuids:         
            timezone = stream_uuids_and_metadata[uuid].get('Metadata/Timezone', None)            
                 
            query = "uuid = '{uuid}'".format(uuid = uuid)   
            logger.debug(query)     
            data = c.prev(query, time.time())
            logger.debug(str(data))
            #data = c.latest(query)
            readings = data[0]['Readings']
            if not readings:
                logger.debug("did not find any readings")
                continue
             
            ts = readings[0][0]
            val = readings[0][1]
            logger.debug("ts=\t{ts}\nval=\t{val}".format(ts=ts, val=val))
            
            ts = ts / 1000.0            
            logger.debug("ts=\t{ts}\nval=\t{val}".format(ts=ts, val=val))        
            if val == None:
                val = float("NaN")
             
            if not newest_ts or newest_ts < ts:
                newest_ts = ts
                newest_val = val
                newest_uuid = uuid
                timezone_of_newest_point = timezone
    except Exception as e:
        logger.debug("Error trying to get latest point from sMAP:\t{e}".format(e = e))        

    logger.debug("Latest info:\tuuid:\t{uuid}\tts:\t{ts}\tval:\t{val}".format(uuid = newest_uuid, ts = newest_ts, val = newest_val))
    return newest_uuid, newest_ts, newest_val, timezone_of_newest_point

def download_data(smap_root, stream_path, stream_uuids = None, source_name = None, start_time = None, end_time = None):    
    from time import mktime
    
    if smap_root[-1] != "/":
        smap_root += "/"
    c = SmapClient(smap_root + "backend")
    
    if (not stream_uuids):
        stream_uuids_and_metadata = get_stream_UUIDs_and_metadata(smap_root, stream_path, source_name)
        
    if not start_time:
        start_time = datetime(1980,1,1)
    if not end_time:
        end_time = datetime.now() + timedelta(days=1)

    try:
        start_time = int(mktime(start_time.timetuple()))
    except:
        pass #assume for the moment that it is already in smap time format
    
    try:
        end_time = int(mktime(end_time.timetuple()))
    except:
        pass #assume for the moment that it is already in smap time format
    
    all_data = []
    
    stream_uuids = stream_uuids_and_metadata.keys()
    timezone = None
        
    for uuid in stream_uuids:
        timezone = stream_uuids_and_metadata[uuid].get('Metadata/Timezone', None)
        uuid, data = c.data("uuid = '{uuid}'".format(uuid=uuid), start_time, end_time)
        if type(data) is list:
            data = data[0]
        for time_stamp_millisec, val in data:
            if val == None:
                val = float("NaN")
            time_stamp = time_stamp_millisec / 1000.0            
            all_data.append((time_stamp, val))
    
    sorted_data = sorted(all_data, key = lambda x : x[0])
    
    return sorted_data, timezone
