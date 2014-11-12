#!/bin/bash

UPDATE=0
PWD=`pwd`

echo "(Info) Installing dependent packages for autoscaler..."

SYSOUT=`cat /etc/*release | awk '/CentOS release 6/{print 6}'`
if [ "$SYSOUT" ]
then
	echo "(Info) Targated OS Centos 6"
else
	echo "(Warning) This script is Centos 6 specific"
	exit 1
fi

echo "(Info) Updating packages"
yum -y update yum-skip-broken

for pkg in git wget vim-enhanced
do
	cmd=`rpm -q $pkg 2>&1`
	rv=$?
	if [ $rv -eq 0 ];then
		echo "(Info) $pkg already installed"
	else
		echo "(Info) Installing $pkg"
		cmd="yum install -y $pkg"
		SYSOUT=`$cmd 2>&1`
		rv=$?
		if [ $rv -ne 0 ];then
			echo "(Error) $cmd"
			echo "$SYSOUT"
			exit 1
		fi
	fi
done

rv=`yum repolist all  | grep epel`
if [ ! "$rv" ];then
	echo "(Info) getting & install epel repo"
	#http://www.cyberciti.biz/faq/fedora-sl-centos-redhat6-enable-epel-repo/
	cmd='wget http://mirror-fpt-telecom.fpt.net/fedora/epel/6/i386/epel-release-6-8.noarch.rpm'
	SYSOUT=`$cmd 2>&1`
	rv=$?
	if [ $rv -ne 0 ];then
		echo "(Error) $cmd"
		echo "$SYSOUT"
		exit 1
	fi
	cmd="rpm -ivh epel-release-6-8.noarch.rpm"
	SYSOUT=`$cmd 2>&1`
	rv=$?
	if [ $rv -ne 0 ];then
		echo "(Error) $cmd"
		echo "$SYSOUT"
		exit 1
	fi
else
	echo "(Info) epel repo already exists"
fi

if [ ! -f /etc/yum.repos.d/rackspace-cloud-monitoring.repo ];then
	#http://www.rackspace.com/knowledge_center/article/install-the-cloud-monitoring-agent#Install
	cmd='curl https://monitoring.api.rackspacecloud.com/pki/agent/redhat-6.asc -o /tmp/signing-key.asc'
	SYSOUT=`$cmd 2>&1`
	rv=$?
	if [ $rv -ne 0 ];then
		echo "(Error) $cmd"
		echo "$SYSOUT"
		exit 1
	fi
	
	cmd="rpm --import /tmp/signing-key.asc"
	SYSOUT=`$cmd 2>&1`
	rv=$?
	if [ $rv -ne 0 ];then
		echo "(Error) $cmd"
		echo "$SYSOUT"
		exit 1
	fi

echo "[rackspace]
name=Rackspace Monitoring
baseurl=http://stable.packages.cloudmonitoring.rackspace.com/centos-6-x86_64
enabled=1">/etc/yum.repos.d/rackspace-cloud-monitoring.repo
	echo "(Info) added rackspace-cloud-monitoring repo"
	UPDATE=1
else
	echo "(Info) rackspace-cloud-monitoring repo already exists"
fi

echo "(Info) checking rackspace-monitoring-agent package"
SYSOUT=`rpm -q rackspace-monitoring-agent 2>&1`
rv=$?
if [ $rv -eq 0 ];then
	echo "(Info) rackspace-monitoring-agent already installed"
else
	yum install -y rackspace-monitoring-agent
fi

UPDATE=1
if [ $UPDATE -eq 1 ];then
	for pkg in python python-devel python-pip make
	do
		echo "(Info) Installing $pkg"
		cmd="yum install -y $pkg"
		SYSOUT=`$cmd 2>&1`
		rv=$?
		if [ $rv -ne 0 ];then
			echo "(Error) $cmd"
			echo "$SYSOUT"
			exit 1
		fi
	done
fi

if [ -f epel-release-6-8.noarch.rpm ];then
	echo "(Info) Cleaning up.."
	`rm -rf  epel-release-* 2>&1`
fi
echo "" 
echo "Please execute following to start monitoring-agent:"
echo "" 
echo "  rackspace-monitoring-agent --setup --username <USERNAME> --apikey <API_KEY>"
echo "" 
echo "  service rackspace-monitoring-agent start"
echo ""
