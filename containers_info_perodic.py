'''
Author: OpsMx
Description: Retrives the docker containers details(Runs every 5m)
'''
import os
import time
import json
import traceback
import requests
import datetime
import netifaces
from pybrctl import BridgeController


interval=300
hostname=os.uname()[1]
tenant_name=os.environ['key']
interface_ip_list=list()
bridges_ip=list()
local_container_data=dict()
host_dicts=dict()#{<Interface_IP>-<MAP-Port>:[ip,cid,cname,]}
docker_info=list()

headers = {'content-type': 'application/json'}
info_url="http://52.8.104.253:8161/n42-services/resources/appdiscovery/updateContainerDetails"

files={"tcp_stats":"/proc/net/tcp",
       "docker-info":"/var/lib/docker/containers/{}/config.v2.json",
       "containers":"/var/lib/docker/containers"}

def wipe_varibles():
    global docker_info,host_dicts,local_container_data,bridges_ip,interface_ip_list
    interface_ip_list=[]
    bridges_ip=[]
    local_container_data.clear()
    host_dicts.clear()
    docker_info=[]

def set_interface_ips():
    global interface_ip_list, bridges_ip
    brctl = BridgeController()
    bridge_iface=list()
    _bridge_names=list()
    for iface in brctl.showall():
        _bridge_names=str(iface)
        bridges_ip.append(netifaces.ifaddresses(str(iface))[2][0]["addr"])
    for iface1 in netifaces.interfaces():
        iface_atri=netifaces.ifaddresses(iface1).keys()
        if iface1 not in _bridge_names and 2 in iface_atri:
            interface_ip_list.append(netifaces.ifaddresses(iface1)[2][0]["addr"])

def get_service(port_list,label):
    try:
        if label:
            return label["service"]
    except:
        if port_list and  port_list[0]["actual-port"] in port_dictionary.port_dict:
            return port_dictionary.port_dict[port_list[0]["actual-port"]]
        else:
            return "unknown"

def set_docker_info():
    global interface_ip_list, host_dicts, local_container_data, docker_info
    global_container_data=dict()
    container_id=os.listdir(files["containers"])# Get the List of Container IDS
    for ids in container_id: #Iter the CID to get container details
        if ids:
            port_list=list()
            try:
                f=open(files["docker-info"].format(ids),'r')
            except:
                continue
            data = json.load(f)
            if data["State"]["Running"]:
                ip_addresses=list()
                for key,value in data["NetworkSettings"]["Ports"].items():
                    ip=[data["NetworkSettings"]["Networks"][a]["IPAddress"] for a in data["NetworkSettings"]["Networks"]]
                    if not value:
                        continue
                    for ports in value:
                        if ports["HostIp"]=="0.0.0.0":
                            for ips in interface_ip_list:
                                global_container_data[ips+":"+ports["HostPort"]]={"cid":ids[:12],"port":key.split("/")[0],"cname":data["Name"].lstrip("/"),"ip":ip,"hostname":hostname}
                        else:
                            global_container_data[ports["HostIp"]+":"+ports["HostPort"]]={"cid":ids[:12],"port":key.split("/")[0],"cname":data["Name"].lstrip("/")}
                        port_list.append({"map-port":ports["HostPort"],"actual-port":key.split("/")[0]})
                for v1 in data["NetworkSettings"]["Networks"].values():
                    local_container_data[v1["IPAddress"]]=[port_list,ids[:12],data["Name"].lstrip("/")]
                    ip_addresses.append(v1["IPAddress"])
                service_name=get_service(port_list,data["Config"]["Labels"])
                docker_info.append({"cid":ids[:12],"cname":data["Name"].lstrip("/"),"hostname":hostname,"pid":data["State"]["Pid"],"ip":ip_addresses,"image":data["Config"]["Image"],"Tenant_Name":tenant_name,"labels":data["Config"]["Labels"],"service":service_name})
    json_data=json.dumps(docker_info)
    print "=================== Docker Info ===================\n"
    print json_data
    response = requests.post(info_url, data=json_data,headers=headers)
    print response,"\n"

while True:
    try:
        wipe_varibles()
        set_interface_ips()
        set_docker_info()
        print "Completed",datetime.datetime.now()
        time.sleep(interval)
    except:
        wipe_varibles()
        print "================ Something Went Wrong. TRACEBACK BELOW ================\n"
        print traceback.format_exc()
        print "\nTIMESTAMP",datetime.datetime.now(),"\n"
