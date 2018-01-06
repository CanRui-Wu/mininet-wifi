"""
    Mininet-WiFi: A simple networking testbed for Wireless OpenFlow/SDWN!
author: Ramon Fontes (ramonrf@dca.fee.unicamp.br)
"""

import os
import random
import sys
from time import sleep

from mininet.log import info, error
from mininet.wifi.link import TCLinkWirelessAP, TCLinkWirelessStation
from mininet.util import macColonHex

from mininet.wifi.node import AccessPoint, AP, Station, Car
from mininet.wifi.wmediumdConnector import WmediumdStarter, WmediumdServerConn
from mininet.wifi.link import wirelessLink, wmediumd
from mininet.wifi.devices import deviceDataRate
from mininet.wifi.mobility import mobility
from mininet.wifi.plot import plot2d, plot3d, plotGraph
from mininet.wifi.module import module
from mininet.wifi.propagationModels import propagationModel
from mininet.wifi.vanet import vanet

sys.path.append(str(os.getcwd()) + '/mininet/')
from mininet.sumo.runner import sumo


class mininetWiFi(object):

    mobilityparam = dict()
    AC = ''
    alternativeModule = ''
    prop_model_name = ''
    alreadyPlotted = False
    configureWiFiDirect = False
    configure4addr = False
    DRAW = False
    enable_interference = False
    enable_spec_prob_link = False
    enable_error_prob = False
    ifb = False
    isMobility = False
    isVanet = False
    isWiFi = False
    rec_rssi = False
    plot = plot2d
    enable_wmediumd = False
    ppm_is_set = False
    n_radios = 0
    min_x = 0
    min_y = 0
    min_z = 0
    max_x = 0
    max_y = 0
    max_z = 0
    nroads = 0
    connections = {}
    wlinks = []

    @classmethod
    def addParameters(cls, node, autoSetMacs, params, mode='managed'):
        """adds parameters to wireless nodes
        node: node
        autoSetMacs: set MAC addrs automatically like IP addresses
        params: parameters
        defaults: Default IP and MAC addresses
        mode: if interface is running in managed or master mode
        """
        node.params['frequency'] = []
        node.params['channel'] = []
        node.params['mode'] = []
        node.params['wlan'] = []
        node.params['mac'] = []
        node.phyID = []
        node.autoTxPower = False

        if 'passwd' in params:
            node.params['passwd'] = []
            passwd_list = params['passwd'].split(',')
            for passwd in passwd_list:
                node.params['passwd'].append(passwd)

        if 'encrypt' in params:
            node.params['encrypt'] = []
            encrypt_list = params['encrypt'].split(',')
            for encrypt in encrypt_list:
                node.params['encrypt'].append(encrypt)

        if mode == 'managed':
            node.params['apsInRange'] = []
            node.params['associatedTo'] = []
            if not cls.enable_interference:
                node.params['rssi'] = []
            node.ifaceToAssociate = 0
            node.max_x = 0
            node.max_y = 0
            node.min_x = 0
            node.min_y = 0
            node.max_v = 0
            node.min_v = 0

            # max_speed
            if 'max_speed' in params:
                node.max_speed = int(params['max_speed'])
            else:
                node.max_speed = 10

            # min_speed
            if 'min_speed' in params:
                node.min_speed = int(params['min_speed'])
            else:
                node.min_speed = 1

        # speed
        if 'speed' in params:
            node.speed = int(params['speed'])

        # max_x
        if 'max_x' in params:
            node.max_x = int(params['max_x'])

        # max_y
        if 'max_y' in params:
            node.max_y = int(params['max_y'])

        # min_x
        if 'min_x' in params:
            node.min_x = int(params['min_x'])

        # min_y
        if 'min_y' in params:
            node.min_y = int(params['min_y'])

        # min_v
        if 'min_v' in params:
            node.min_v = int(params['min_v'])

        # max_v
        if 'max_v' in params:
            node.max_v = int(params['max_v'])

        # constantVelocity
        if 'constantVelocity' in params:
            node.constantVelocity = int(params['constantVelocity'])
        else:
            node.constantVelocity = 1

        # constantDistance
        if 'constantDistance' in params:
            node.constantDistance = int(params['constantDistance'])
        else:
            node.constantDistance = 1

        # position
        if 'position' in params:
            position = params['position']
            position = position.split(',')
            node.params['position'] = [float(position[0]),
                                       float(position[1]),
                                       float(position[2])]
        else:
            if 'position' in node.params:
                position = node.params['position']
                position = position.split(',')
                node.params['position'] = [float(position[0]),
                                           float(position[1]),
                                           float(position[2])]

        wlans = cls.countWiFiIfaces(params)

        for wlan in range(wlans):
            cls.addParamsToNode(node)
            if mode == 'managed':
                cls.appendAssociatedTo(node)

            if mode == 'master':
                if 'phywlan' in node.params and wlan == 0:
                    node.params['wlan'].append(node.params['phywlan'])
                else:
                    node.params['wlan'].append(node.name + '-wlan' + str(wlan + 1))
                if 'link' in params and params['link'] == 'mesh':
                    cls.appendRSSI(node)
                    cls.appendAssociatedTo(node)
            else:
                node.params['wlan'].append(node.name + '-wlan' + str(wlan))
                cls.appendRSSI(node)
            node.params.pop("wlans", None)

        if mode == 'managed':
            cls.addMacParamToNode(node, wlans, autoSetMacs, params)
            cls.addIpParamToNode(node, wlans, autoSetMacs, params)

        cls.addAntennaGainParamToNode(node, wlans, params)
        cls.addAntennaHeightParamToNode(node, wlans, params)
        cls.addTxPowerParamToNode(node, wlans, params)
        cls.addChannelParamToNode(node, wlans, params)
        cls.addModeParamToNode(node, wlans, params)
        cls.addRangeParamToNode(node, wlans, params)

        # Equipment Model
        equipmentModel = ("%s" % params.pop('equipmentModel', {}))
        if equipmentModel != "{}":
            node.equipmentModel = equipmentModel

        if mode == 'master' or 'ssid' in node.params:
            node.params['associatedStations'] = []
            node.params['stationsInRange'] = {}
            node._4addr = False

            if 'config' in node.params:
                config = node.params['config']
                if config != []:
                    config = node.params['config'].split(',')
                    for conf in config:
                        if 'wpa=' in conf or 'wep=' in conf:
                            node.params['encrypt'] = []
                        if 'wpa=' in conf:
                            node.params['encrypt'].append('wpa')
                        if 'wep=' in conf:
                            node.params['encrypt'].append('wep')

            if mode == 'master':
                node.params['mac'] = []
                node.params['mac'].append('')
                if 'mac' in params:
                    node.params['mac'][0] = params[ 'mac' ]

                if 'ssid' in params:
                    node.params['ssid'] = []
                    ssid_list = params['ssid'].split(',')
                    for ssid in ssid_list:
                        node.params['ssid'].append(ssid)

    @classmethod
    def addParamsToNode(cls, node):
        "Add Frequency, func and phyID"
        node.params['frequency'].append(2.412)
        node.func.append('none')
        node.phyID.append(0)

    @classmethod
    def appendAssociatedTo(cls, node):
        "Add associatedTo param"
        node.params['associatedTo'].append('')

    @classmethod
    def appendRSSI(cls, node):
        "Add RSSI param"
        if not cls.enable_interference:
            node.params['rssi'].append(-60)

    @classmethod
    def addRangeParamToNode(cls, node, wlans=0, params=None):
        "Add Signal Range Param"
        node.params['range'] = []
        if 'range' in params:
            range_list = str(params['range']).split(',')
            for value in range_list:
                node.params['range'].append(float(value))
                node.setRange(float(value), intf=node.params['wlan'][0])
            if len(range_list) != wlans:
                error('*** Error (%s): signal range length'
                      'differs from the number of interfaces!' % node.name)
                exit(1)
        else:
            for _ in range(0, wlans):
                node.params['range'].append(0)

    @classmethod
    def addIpParamToNode(cls, node, wlans=0, autoSetMacs=False,
                         params=None, isVirtualIface=False):
        "Add IP Param"
        if isVirtualIface:
            node.params['ip'].append(node.params['ip'][0])
        else:
            node.params['ip'] = []
            if 'ip' in params:
                ip_list = params['ip'].split(',')
                for ip in ip_list:
                    node.params['ip'].append(ip)
                if len(ip_list) != len(node.params['wlan']):
                    for ip_list in range(len(ip_list),
                                         len(node.params['wlan'])):
                        node.params['ip'].append('0/0')
            elif autoSetMacs:
                for n in range(wlans):
                    node.params['ip'].append('0/0')
                    node.params['ip'][n] = params[ 'ip' ]
            else:
                for _ in range(wlans):
                    node.params['ip'].append('')

    @classmethod
    def addMacParamToNode(cls, node, wlans=0, autoSetMacs=False,
                          params=None, isVirtualIface=False, macID=0):
        "Add Mac Param"
        if isVirtualIface:
            new_mac = list(node.params['mac'][0])
            new_mac[7] = str(macID)
            node.params['mac'].append("".join(new_mac))
        else:
            node.params['mac'] = []
            if 'mac' in params:
                mac_list = params['mac'].split(',')
                for mac in mac_list:
                    node.params['mac'].append(mac)
                if len(mac_list) != wlans:
                    for _ in range(len(mac_list), wlans):
                        node.params['mac'].append('')
            elif autoSetMacs:
                for n in range(wlans):
                    node.params['mac'].append('')
                    node.params['mac'][n] = params[ 'mac' ]
            else:
                for _ in range(wlans):
                    node.params['mac'].append('')

    @classmethod
    def addAntennaHeightParamToNode(cls, node, wlans=0, params=None,
                                    isVirtualIface=False):
        "Add Antenna Height Param"
        if isVirtualIface:
            node.params['antennaHeight'].append(
                float(node.params['antennaHeight'][0]))
        else:
            node.params['antennaHeight'] = []
            if 'antennaHeight' in params:
                antennaHeight_list = params['antennaHeight'].split(',')
                for antennaHeight in antennaHeight_list:
                    node.params['antennaHeight'].append(float(antennaHeight))
            else:
                for _ in range(wlans):
                    node.params['antennaHeight'].append(1.0)

    @classmethod
    def addAntennaGainParamToNode(cls, node, wlans=0, params=None,
                                  isVirtualIface=False):
        "Add Antenna Gain Param"
        if isVirtualIface:
            node.params['antennaGain'].append(
                float(node.params['antennaGain'][0]))
        else:
            node.params['antennaGain'] = []
            if 'antennaGain' in params:
                antennaGain_list = params['antennaGain'].split(',')
                for antennaGain in antennaGain_list:
                    node.params['antennaGain'].append(float(antennaGain))
            else:
                for _ in range(wlans):
                    node.params['antennaGain'].append(5.0)

    @classmethod
    def addModeParamToNode(cls, node, wlans=0, params=None,
                           isVirtualIface=False):
        "Add Mode Param"
        if isVirtualIface:
            node.params['mode'].append(node.params['mode'][0])
        else:
            node.params['mode'] = []
            if 'mode' in params:
                mode_list = params['mode'].split(',')
                for mode in mode_list:
                    node.params['mode'].append(mode)
                if len(mode_list) != len(node.params['wlan']):
                    for mode_list in range(len(mode_list),
                                           len(node.params['wlan'])):
                        node.params['mode'].append(node.params['mode'][0])
            else:
                for _ in range(wlans):
                    node.params['mode'].append(params['mode'])

    @classmethod
    def addChannelParamToNode(cls, node, wlans=0, params=None,
                              isVirtualIface=False):
        "Add Channel Param"
        if isVirtualIface:
            node.params['channel'].append(node.params['channel'][0])
        else:
            node.params['channel'] = []
            if 'channel' in params:
                channel_list = params['channel'].split(',')
                for channel in channel_list:
                    node.params['channel'].append(channel)
                if len(channel_list) != len(node.params['wlan']):
                    for channel_list in range(len(channel_list),
                                              len(node.params['wlan'])):
                        node.params['channel'].append(node.params['channel'][0])
            else:
                for _ in range(wlans):
                    node.params['channel'].append(1)

    @classmethod
    def addTxPowerParamToNode(cls, node, wlans=0, params=None,
                              isVirtualIface=False):
        "Add Tx Power Param"
        if isVirtualIface:
            node.params['txpower'].append(node.params['txpower'][0])
        else:
            node.params['txpower'] = []
            if 'txpower' in params:
                txpower_list = params['txpower'].split(',')
                for txpower in txpower_list:
                    node.params['txpower'].append(int(txpower))
            else:
                for _ in range(wlans):
                    node.params['txpower'].append(14)

    @classmethod
    def countWiFiIfaces(cls, params):
        "Count the number of virtual wifi interfaces"
        if 'wlans' in params:
            cls.n_radios += int(params['wlans'])
            wlans = int(params['wlans'])
        else:
            wlans = 1
            cls.n_radios += 1
        return wlans

    @classmethod
    def createVirtualIfaces(cls, nodes):
        "Creates virtual wifi interfaces"
        for node in nodes:
            if 'nvif' in node.params:
                nvif = node.params['nvif']
                wlan = 0
                for vif_ in range(0, nvif):
                    vif = node.params['wlan'][wlan] + str(vif_ + 1)
                    node.params['wlan'].append(vif)
                    node.params['range'].append(node.params['range'][0])
                    cls.addParamsToNode(node)
                    cls.addTxPowerParamToNode(node, isVirtualIface=True)
                    cls.addChannelParamToNode(node, isVirtualIface=True)
                    cls.addMacParamToNode(node, isVirtualIface=True,
                                          macID=(vif_ + 1))
                    cls.appendRSSI(node)
                    cls.appendAssociatedTo(node)
                    cls.addAntennaGainParamToNode(node, isVirtualIface=True)
                    cls.addAntennaHeightParamToNode(node, isVirtualIface=True)
                    cls.addModeParamToNode(node, isVirtualIface=True)
                    node.cmd('iw dev %s interface add %s type station'
                             % (node.params['wlan'][wlan], vif))
                    TCLinkWirelessStation(node, intfName1=vif)
                    cls.configureMacAddr(node)

    @classmethod
    def addMesh(cls, node, **params):
        """
        Configure wireless mesh
        node: name of the node
        cls: custom association class/constructor
        params: parameters for node
        """
        if 'intf' in params:
            for intf_ in node.params['wlan']:
                if params['intf'] == intf_:
                    wlan = node.params['wlan'].index(intf_)
        else:
            wlan = node.ifaceToAssociate

        node.func[wlan] = 'mesh'

        if isinstance(node, AP):
            pass
        else:
            node.params['ssid'] = []
            for _ in range(len(node.params['wlan'])):
                node.params['ssid'].append('')

        ssid = ("%s" % params['ssid'])
        if ssid != "{}":
            node.params['ssid'][wlan] = ssid
        else:
            node.params['ssid'][wlan] = 'meshNetwork'

        if node.autoTxPower:
            intf = node.params['wlan'][wlan]
            node.params['range'][wlan] = node.getRange(intf=intf, noiseLevel=95)

        node.setMeshIface(node.params['wlan'][wlan], **params)

        if 'intf' not in params:
            node.ifaceToAssociate += 1

    @classmethod
    def addHoc(cls, node, **params):
        """
        Configure AdHoc
        node: name of the node
        cls: custom association class/constructor
        params: parameters for station
        """
        if 'intf' in params:
            for intf_ in node.params['wlan']:
                if params['intf'] == intf_:
                    wlan = node.params['wlan'].index(intf_)
        else:
            wlan = node.ifaceToAssociate

        node.func[wlan] = 'adhoc'

        node.params['ssid'] = []
        for _ in range(0, len(node.params['wlan'])):
            node.params['ssid'].append('')

        ssid = ("%s" % params.pop('ssid', {}))
        if ssid != "{}":
            node.params['ssid'][wlan] = ssid
            node.params['associatedTo'][wlan] = ssid
        else:
            node.params['ssid'][wlan] = 'adhocNetwork'
            node.params['associatedTo'][wlan] = 'adhocNetwork'

        if not node.autoTxPower:
            intf = node.params['wlan'][wlan]
            node.params['range'][wlan] = node.getRange(intf=intf, noiseLevel=95)

        if 'channel' in params:
            node.setChannel(params['channel'], intf=node.params['wlan'][wlan])

        node.configureAdhoc(wlan, cls.enable_wmediumd)
        if 'intf' not in params:
            node.ifaceToAssociate += 1

    @classmethod
    def wifiDirect(cls, node, **params):
        """
        Configure wifidirect
        node: name of the node
        cls: custom association class/constructor
        params: parameters for station
        """
        if 'intf' in params:
            for intf_ in node.params['wlan']:
                if params['intf'] == intf_:
                    wlan = node.params['wlan'].index(intf_)
        else:
            wlan = node.ifaceToAssociate

        node.func[wlan] = 'wifiDirect'

        cmd = ("echo \'")
        cmd = cmd + 'ctrl_interface=/var/run/wpa_supplicant\
            \nap_scan=1\
            \np2p_go_ht40=1\
            \ndevice_name=%s-%s\
            \ndevice_type=1-0050F204-1\
            \np2p_no_group_iface=1' % (node, wlan)
        confname = "mn%d_%s-%s_wifiDirect.conf" % (os.getpid(), node, wlan)
        cmd = cmd + ("\' > %s" % confname)
        os.system(cmd)
        node.cmd('wpa_supplicant -B -Dnl80211 -c%s -i%s -d'
                 % (confname, node.params['wlan'][wlan]))
        if 'intf' not in params:
            node.ifaceToAssociate += 1

        p2p_mac = node.cmd('iw dev | grep addr | awk \'NR==1\' | '
                           'awk \'{print $2};\'')
        node.params['mac'].append(p2p_mac.splitlines()[0])
        node.params['wlan'].append('0')
        node.params['txpower'].append(node.params['txpower'][0])
        node.func.append('wifiDirect')

    @staticmethod
    def randMac():
        "Return a random, non-multicast MAC address"
        return macColonHex(random.randint(1, 2 ** 48 - 1) & 0xfeffffffffff |
                           0x020000000000)

    @classmethod
    def checkAPAdhoc(cls, stations, aps):
        """
        configure APAdhoc

        :param stations: list of stations
        :param aps: list of access points
        """
        isApAdhoc = []
        for sta in stations:
            if sta.func[0] == 'ap':
                aps.append(sta)
                isApAdhoc.append(sta)

        for ap in isApAdhoc:
            stations.remove(ap)
            ap.setIP('%s' % ap.params['ip'][0], intf='%s' % ap.params['wlan'][0])
            ap.params.pop('rssi', None)
            ap.params.pop('apsInRange', None)
            ap.params.pop('associatedTo', None)

            for _ in (1, len(ap.params['wlan'])):
                ap.params['mac'].append('')

        return stations, aps

    @classmethod
    def restartNetworkManager(cls):
        """Restart network manager if the mac address of the AP is not included at
        /etc/NetworkManager/NetworkManager.conf"""
        nm_is_running = os.system('service network-manager status 2>&1 | grep -ic '
                                  'running >/dev/null 2>&1')
        if AccessPoint.writeMacAddress and nm_is_running != 256:
            info('Mac Address(es) of AP(s) is(are) being added into '
                 '/etc/NetworkManager/NetworkManager.conf\n')
            info('Restarting network-manager...\n')
            os.system('service network-manager restart')
        AccessPoint.writeMacAddress = False

    @classmethod
    def kill_hostapd(cls):
        "Kill hostapd"
        module.kill_hostapd()
        sleep(0.1)

    @classmethod
    def kill_wmediumd(cls):
        "Kill wmediumd"
        info("\n*** Killing wmediumd")
        WmediumdServerConn.disconnect()
        WmediumdStarter.stop()
        sleep(0.1)

    @classmethod
    def kill_mac80211_hwsim(cls):
        "Kill mac80211_hwsim"
        module.kill_mac80211_hwsim()
        sleep(0.1)

    @classmethod
    def verifyNetworkManager(cls, node):
        """
        First verify if the mac address of the ap is included at
        NetworkManager.conf

        :param node: node
        :param wlanID: wlan ID
        """
        for wlan in range(len(node.params['wlan'])):
            if 'inNamespace' not in node.params:
                if not isinstance(node, Station):
                    options = dict()
                    if 'phywlan' in node.params and wlan == 0:
                        iface = node.params['phywlan']
                        options.setdefault('intfName1', iface)
                    else:
                        cls.configureIface(node, wlan)
                    TCLinkWirelessAP(node, **options)
            elif 'inNamespace' in node.params:
                cls = TCLinkWirelessAP
                cls(node)
            AccessPoint.setIPMAC(node, wlan)
            if 'vssids' in node.params:
                break

    @classmethod
    def configureIface(cls, node, wlan):
        intf = module.wlan_list[0]
        module.wlan_list.pop(0)
        node.renameIface(intf, node.params['wlan'][wlan])

    @classmethod
    def configureAP(cls, ap, aplist=None):
        """Configure AP

        :param ap: ap node
        :param wlanID: wlan ID"""
        for wlan in range(len(ap.params['wlan'])):
            if ap.params['ssid'][wlan] != '':
                if 'encrypt' in ap.params and 'config' not in ap.params:
                    if ap.params['encrypt'][wlan] == 'wpa':
                        ap.auth_algs = 1
                        ap.wpa = 1
                        if 'ieee80211r' in ap.params \
                                and ap.params['ieee80211r'] == 'yes':
                            ap.wpa_key_mgmt = 'FT-EAP'
                        else:
                            ap.wpa_key_mgmt = 'WPA-EAP'
                        ap.rsn_pairwise = 'TKIP CCMP'
                        ap.wpa_passphrase = ap.params['passwd'][0]
                    elif ap.params['encrypt'][wlan] == 'wpa2':
                        ap.auth_algs = 1
                        ap.wpa = 2
                        if 'ieee80211r' in ap.params \
                                and ap.params['ieee80211r'] == 'yes' \
                                and 'authmode' not in ap.params:
                            ap.wpa_key_mgmt = 'FT-PSK'
                        elif 'authmode' in ap.params \
                                and ap.params['authmode'] == '8021x':
                            ap.wpa_key_mgmt = 'WPA-EAP'
                        else:
                            ap.wpa_key_mgmt = 'WPA-PSK'
                        ap.rsn_pairwise = 'CCMP'
                        if 'authmode' not in ap.params:
                            ap.wpa_passphrase = ap.params['passwd'][0]
                    elif ap.params['encrypt'][wlan] == 'wep':
                        ap.auth_algs = 2
                        ap.wep_key0 = ap.params['passwd'][0]

                AccessPoint(ap, wlan=wlan, aplist=aplist)

                if 'phywlan' in ap.params and wlan == 0:
                    iface = ap.params['phywlan']
                else:
                    iface = ap.params['wlan'][wlan]

                if not cls.enable_wmediumd:
                    cls.setBw(ap, wlan, iface)

                ap.params['frequency'][wlan] = ap.get_freq(0)

                if 'vssids' in ap.params:
                    break

    @classmethod
    def setBw(cls, node, wlan, iface):
        """ Set bw to AP """
        value = deviceDataRate.apRate(node, wlan)
        bw = value
        node.cmd("tc qdisc replace dev %s \
            root handle 2: tbf rate %sMbit burst 15000 "
                 "latency 1ms" % (iface, bw))
        # Reordering packets
        node.cmd('tc qdisc add dev %s parent 2:1 handle 10: '
                 'pfifo limit 1000' % (iface))

    @classmethod
    def configureAPs(cls, aps, driver):
        """Configure All APs

        :param aps: list of access points
        """
        for ap in aps:
            if 'vssids' in ap.params:
                for i in range(1, ap.params['vssids']+1):
                    ap.params['range'].append(ap.params['range'][0])
                    ap.params['wlan'].append('%s-%s'
                                             % (ap.params['wlan'][0], i))
                    ap.params['mode'].append(ap.params['mode'][0])
                    ap.params['frequency'].append(
                        ap.params['frequency'][0])
                    ap.params['mac'].append('')
            else:
                for i in range(1, len(ap.params['wlan'])):
                    ap.params['mac'].append('')
            ap.params['driver'] = driver
            cls.verifyNetworkManager(ap)
        cls.restartNetworkManager()

        for ap in aps:
            if 'link' not in ap.params:
                cls.configureAP(ap, aplist=aps)
                ap.phyID = module.phyID
                module.phyID += 1

    @classmethod
    def configureWirelessLink(cls, stations, aps, cars):
        """
        Configure Wireless Link

        :param stations: list of stations
        :param aps: list of access points
        :param cars: list of cars
        """
        nodes = stations + cars
        for node in nodes:
            for wlan in range(0, len(node.params['wlan'])):
                TCLinkWirelessStation(node,
                                      intfName1=node.params['wlan'][wlan])
            cls.configureMacAddr(node)
        stations, aps = cls.checkAPAdhoc(stations, aps)
        return stations, aps

    @classmethod
    def plotGraph(cls, min_x=0, min_y=0, min_z=0,
                  max_x=0, max_y=0, max_z=0):
        """
        Plots Graph

        :params max_x: maximum X
        :params max_y: maximum Y
        :params max_z: maximum Z
        """
        cls.DRAW = True
        cls.min_x = min_x
        cls.min_y = min_y
        cls.max_x = max_x
        cls.max_y = max_y
        if max_z != 0:
            cls.min_z = min_z
            cls.max_z = max_z
            cls.plot = plot3d
            mobility.continuePlot = 'plot3d.graphPause()'

    @classmethod
    def checkDimension(cls, nodes):
        try:
            plotGraph(cls.min_x, cls.min_y, cls.min_z,
                      cls.max_x, cls.max_y, cls.max_z,
                      nodes, cls.connections)
            if not issubclass(cls.plot, plot3d):
                cls.plot.plotGraph()
                cls.plot.graphPause()
        except:
            info('Something went wrong. Running without GUI.\n')
            cls.DRAW = False

    @classmethod
    def start_mobility(cls, **kwargs):
        "Starts Mobility"
        cls.isMobility = True

        if 'model' in kwargs or cls.isVanet:
            stationaryNodes = []
            for node in kwargs['mobileNodes']:
                if 'position' not in node.params \
                        or 'position' in node.params \
                                and node.params['position'] == (-1,-1,-1):
                    node.isStationary = False
                    stationaryNodes.append(node)
                    node.params['position'] = 0, 0, 0
            kwargs['stationaryNodes'] = stationaryNodes
            params = cls.setMobilityParams(**kwargs)
            if cls.nroads == 0:
                mobility.start(**params)
            else:
                vanet(**params)

    @classmethod
    def stopMobility(cls, stations, aps, **kwargs):
        "Stops Mobility"
        cls.autoAssociation(stations, aps)
        params = cls.setMobilityParams(**kwargs)
        mobility.stop(**params)

    @classmethod
    def setMobilityParams(cls, **kwargs):
        "Set Mobility Parameters"
        if 'model' in kwargs:
            cls.mobilityparam.setdefault('model', kwargs['model'])
        if cls.nroads != 0:
            cls.mobilityparam.setdefault('nroads', cls.nroads)
        if 'repetitions' in kwargs:
            cls.mobilityparam.setdefault('repetitions', kwargs['repetitions'])
        if 'plotNodes' in kwargs:
            cls.mobilityparam.setdefault('plotNodes', kwargs['plotNodes'])

        if 'model' in kwargs:
            stations = kwargs['stations']
            if 'min_x' in kwargs:
                if not cls.DRAW:
                    cls.min_x = int(kwargs['min_x'])
                for sta in stations:
                    sta.min_x = int(kwargs['min_x'])
            if 'min_y' in kwargs:
                if not cls.DRAW:
                    cls.min_y = int(kwargs['min_y'])
                for sta in stations:
                    sta.min_y = int(kwargs['min_y'])
            if 'max_x' in kwargs:
                if not cls.DRAW:
                    cls.max_x = int(kwargs['max_x'])
                for sta in stations:
                    sta.max_x = int(kwargs['max_x'])
            if 'max_y' in kwargs:
                if not cls.DRAW:
                    cls.max_y = int(kwargs['max_y'])
                for sta in stations:
                    sta.max_y = int(kwargs['max_y'])
            if 'min_v' in kwargs:
                cls.mobilityparam.setdefault('min_v', kwargs['min_v'])
            if 'max_v' in kwargs:
                cls.mobilityparam.setdefault('max_v', kwargs['max_v'])

        if 'time' in kwargs:
            if 'init_time' not in cls.mobilityparam:
                cls.mobilityparam.setdefault('init_time', kwargs['time'])
            else:
                cls.mobilityparam.setdefault('final_time', kwargs['time'])
        if 'seed' in kwargs:
            cls.mobilityparam.setdefault('seed', kwargs['seed'])
        if 'stations' in kwargs:
            cls.mobilityparam.setdefault('stations', kwargs['stations'])
        if 'aps' in kwargs:
            cls.mobilityparam.setdefault('aps', kwargs['aps'])

        cls.mobilityparam.setdefault('DRAW', cls.DRAW)
        cls.mobilityparam.setdefault('connections', cls.connections)
        cls.mobilityparam.setdefault('min_x', cls.min_x)
        cls.mobilityparam.setdefault('min_y', cls.min_y)
        cls.mobilityparam.setdefault('min_z', cls.min_z)
        cls.mobilityparam.setdefault('max_x', cls.max_x)
        cls.mobilityparam.setdefault('max_y', cls.max_y)
        cls.mobilityparam.setdefault('max_z', cls.max_z)
        cls.mobilityparam.setdefault('AC', cls.AC)
        cls.mobilityparam.setdefault('rec_rssi', cls.rec_rssi)
        if 'stationaryNodes' in kwargs and kwargs['stationaryNodes'] is not []:
            cls.mobilityparam.setdefault('stationaryNodes', kwargs['stationaryNodes'])
        return cls.mobilityparam

    @classmethod
    def useExternalProgram(cls, **params):
        """
        Opens an external program

        :params program: any program (useful for SUMO)
        :params **params config_file: file configuration
        """
        cls.isVanet = True
        for car in params['cars']:
            car.params['position'] = 0, 0, 0
        if params['program'] == 'sumo' or params['program'] == 'sumo-gui':
            sumo(**params)

    @classmethod
    def configureMacAddr(cls, node):
        """
        Configure Mac Address

        :param node: node
        """
        for wlan in range(0, len(node.params['wlan'])):
            iface = node.params['wlan'][wlan]
            if node.params['mac'][wlan] == '':
                node.params['mac'][wlan] = node.getMAC(iface)
            else:
                mac = node.params['mac'][wlan]
                node.setMAC(mac, iface)

    @classmethod
    def configureWifiNodes(cls, mn):
        "Configure WiFi Nodes"
        cls.enable_wmediumd = mn.enable_wmediumd

        params = {}
        if cls.ifb:
            wirelessLink.ifb = True
            params['ifb'] = cls.ifb
        nodes = mn.stations + mn.aps + mn.cars
        module.start(nodes, cls.n_radios, cls.alternativeModule, **params)
        cls.configureWirelessLink(mn.stations, mn.aps, mn.cars)
        cls.createVirtualIfaces(mn.stations)
        cls.configureAPs(mn.aps, mn.driver)
        cls.isWiFi = True
        cls.rec_rssi = mn.rec_rssi

        for car in mn.cars:
            # useful if there no link between sta and any other device
            params = {'nextIP': mn.nextIP, 'ipBaseNum':mn.ipBaseNum,
                      'prefixLen':mn.prefixLen, 'ssid':car.params['ssid']}
            if 'func' in car.params and car.params['func'] == 'adhoc':
                cls.addHoc(car.params['carsta'], **params)
            else:
                cls.addMesh(car.params['carsta'], **params)
                mn.stations.remove(car.params['carsta'])
            mn.stations.append(car)
            if 'position' in car.params:
                if car.params['position'] == (0,0,0):
                    car.lastpos = [0, 0, 0]
                else:
                    car.params['carsta'].params['position'] = car.params['position']
                    car.lastpos = car.params['position']
            else:
                car.lastpos = [0, 0, 0]
            car.params['wlan'].append(0)
            if not cls.enable_interference:
                car.params['rssi'].append(0)
            car.params['channel'].append(0)
            car.params['mode'].append(0)
            car.params['txpower'].append(0)
            car.params['antennaGain'].append(0)
            car.params['antennaHeight'].append(0)
            car.params['associatedTo'].append('')
            car.params['frequency'].append(0)

        for node in nodes:
            for wlan in range(0, len(node.params['wlan'])):
                if isinstance(node, Car) and wlan == 1:
                    node = node.params['carsta']
                    wlan = 0
                if int(node.params['range'][wlan]) == 0:
                    if isinstance(node, Car) and wlan == 1:
                        node = node.params['carsta']
                        wlan = 0
                    intf = node.params['wlan'][wlan]
                    node.params['range'][wlan] = node.getRange(intf=intf)
                else:
                    if node.params['txpower'][wlan] == 14:
                        node.autoTxPower=True
                        node.params['txpower'][wlan] = \
                            node.get_txpower_prop_model(wlan)
                    setParam = True
                    if isinstance(node, Car):
                        setParam = False
                    node.setTxPower(node.params['txpower'][wlan],
                                    intf=node.params['wlan'][wlan],
                                    setParam=setParam)

        if cls.enable_wmediumd:
            if not mn.configureWiFiDirect and not mn.configure4addr and \
                    not mn.enable_error_prob:
                if mn.enable_interference:
                    mn.wmediumd_mode = 'interference'
                elif mn.enable_error_prob:
                    mn.wmediumd_mode = 'error_prob'
                else:
                    mn.wmediumd_mode = None

                wmediumd(mn.wmediumd_mode, mn.fading_coefficient, mn.stations,
                         mn.aps, propagationModel)

                if mn.enable_interference and not cls.isVanet:
                    for node in nodes:
                        for wlan in range(0, len(node.params['wlan'])):
                            node.setTxPower(node.params['txpower'][wlan],
                                            intf=node.params['wlan'][wlan],
                                            setParam=False)
                            node.setAntennaGain(node.params['antennaGain'][wlan],
                                                intf=node.params['wlan'][wlan],
                                                setParam=False)
        return mn.stations, mn.aps

    @classmethod
    def plotCheck(cls, stations, aps, other_nodes):
        "Check which nodes will be plotted"
        stas, aps = cls.checkAPAdhoc(stations, aps)
        if mobility.aps == []:
            mobility.aps = aps
        if mobility.stations == []:
            mobility.stations = stations

        nodes = other_nodes

        for ap in aps:
            if 'position' in ap.params:
                nodes.append(ap)

        for sta in stations:
            if 'position' in sta.params:
                nodes.append(sta)

        cls.checkDimension(nodes)

        if propagationModel.model == 'logNormalShadowing':
            while True:
                for node in nodes:
                    intf = node.params['wlan'][0]
                    node.params['range'][0] = node.getRange(intf=intf)
                    if cls.DRAW:
                        if not issubclass(cls.plot, plot3d):
                            cls.plot.updateCircleRadius(node)
                        cls.plot.graphUpdate(node)
                if cls.DRAW:
                    cls.plot.graphUpdate(node)
                eval(mobility.continuePlot)
                sleep(0.5)
        return stas, aps

    @classmethod
    def autoAssociation(cls, stations, aps):
        """
        This is useful to make the users' life easier

        :param stations: list of stations
        :param aps: list of access points
        """
        nodes = stations + aps
        for node in nodes:
            for wlan in range(0, len(node.params['wlan'])):
                if isinstance(node, Car) and wlan == 1:
                    node = node.params['carsta']
                    wlan = 0
        ap = []
        for node in aps:
            if 'link' in node.params:
                ap.append(node)

        nodes = stations + ap

        if cls.nroads == 0:
            for node in nodes:
                if 'position' in node.params and 'link' not in node.params:
                    mobility.aps = aps
                    mobility.parameters_(node)

            for sta in stations:
                for wlan in range(0, len(sta.params['wlan'])):
                    for ap in aps:
                        if 'position' in sta.params and 'position' in ap.params:
                            dist = sta.get_distance_to(ap)
                            if dist <= ap.params['range'][0]:
                                mobility.handover(sta, ap, wlan, ap_wlan=0)
                                if cls.rec_rssi:
                                    os.system('hwsim_mgmt -k %s %s >/dev/null 2>&1'
                                              % (sta.phyID[wlan], abs(int(sta.params['rssi'][wlan]))))

    @classmethod
    def propagation_model(cls, **kwargs):
        "Propagation Model Attr"
        propagationModel.setAttr(**kwargs)

    @classmethod
    def stop_simulation(cls):
        "Pause the simulation"
        mobility.pause_simulation = True

    @classmethod
    def start_simulation(cls):
        "Start the simulation"
        mobility.pause_simulation = False

    @classmethod
    def printDistance(cls, src, dst, nodes):
        """
        Prints the distance between two points

        :params src: source node
        :params dst: destination node
        :params nodes: list of nodes
        """
        try:
            for host1 in nodes:
                if src == str(host1):
                    src = host1
                    for host2 in nodes:
                        if dst == str(host2):
                            dst = host2
                            dist = src.get_distance_to(dst)
                            info("The distance between %s and %s is %.2f "
                                 "meters\n" % (src, dst, float(dist)))
        except:
            info("node %s or/and node %s does not exist or there is no " \
                 "position defined\n" % (dst, src))

    @classmethod
    def configureMobility(cls, *args, **kwargs):
        "Configure mobility parameters"
        args[0].isStationary = False
        mobility.configure(*args, **kwargs)

    @classmethod
    def setDataRate(cls, sta=None, ap=None, wlan=0):
        "Set the rate"
        value = deviceDataRate(sta, ap, wlan)
        return value

    @classmethod
    def associationControl(cls, ac):
        """Defines an association control
        :params ac: association control method
        """
        mobility.AC = ac

    @classmethod
    def setChannelEquation(cls, **params):
        """
        Set Channel Equation. The user may change the equation defined in
        wifiChannel.py by any other.

        :params bw: bandwidth (mbps)
        :params delay: delay (ms)
        :params latency: latency (ms)
        :params loss: loss (%)
        """
        if 'bw' in params:
            wirelessLink.equationBw = params['bw']
        if 'delay' in params:
            wirelessLink.equationDelay = params['delay']
        if 'latency' in params:
            wirelessLink.equationLatency = params['latency']
        if 'loss' in params:
            wirelessLink.equationLoss = params['loss']

    @classmethod
    def stopGraphParams(cls):
        "Stop the graph"
        mobility.continuePlot = 'exit()'
        mobility.continue_params = 'exit()'
        sleep(0.5)

    @classmethod
    def closeMininetWiFi(cls):
        "Close Mininet-WiFi"
        cls.plot.closePlot()
        module.stop()  # Stopping WiFi Module