#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib2

coredns_config = """
. {
    forward . 127.0.0.1:5353 {
        except {{ domains }}
    }
    proxy . 119.29.29.29 114.114.114.114 {
        policy round_robin
    }
    log
    cache
    health
}

.:5353 {
    forward . tls://8.8.8.8 tls://8.8.4.4 {
        tls_servername dns.google
        health_check 5s
    }
    cache 30
}


.:15353 {
    forward . tls://1.1.1.1 tls://1.0.0.1 {
        tls_servername cloudflare-dns.com
        health_check 5s
    }
    cache 30
}

.:25353 {
    forward . tls://9.9.9.9 {
        tls_servername dns.quad9.net
        health_check 5s
    }
    cache 30
}
"""


def url_request(url):
    r = urllib2.urlopen(url)
    return r.read()


def create_conf():
    global coredns_config
    dnsmasq_conf = ''
    dnsmasq_conf += url_request('https://cdn.jsdelivr.net/gh/felixonmars/dnsmasq-china-list/accelerated-domains.china.conf')
    dnsmasq_conf += url_request('https://cdn.jsdelivr.net/gh/felixonmars/dnsmasq-china-list/apple.china.conf')
    dnsmasq_conf += url_request('https://cdn.jsdelivr.net/gh/felixonmars/dnsmasq-china-list/google.china.conf')
    domains = []
    lines = dnsmasq_conf.split('\n')
    for line in lines:
        arr = line.split('/')
        if len(arr) == 3:
            domains.append(arr[1])
    domains = ' '.join(domains)
    coredns_config = coredns_config.replace('{{ domains }}', domains).strip()
    with open('Corefile', 'wb') as f:
        f.write(coredns_config)


def main():
    create_conf()


if __name__ == '__main__':
    main()
