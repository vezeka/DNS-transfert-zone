#!/usr/bin/env python3
# coding: utf-8
# This script tries to do a zone transfer on the target servers listed in a file.

import sys
import re
import dns.name
import dns.resolver
import dns.zone
import dns.query

# Usage
if len(sys.argv) != 2 or sys.argv[1] in ("--help", "-h"):
    print("Usage:", sys.argv[0], "<file_with_domains>\n\n-h or --help: show this message")
    exit(0)







def validate_domain_name(domain):
    if not domain or len(domain) > 253:
        return False  # Reject empty or too long domains
    if domain[-1] == ".":
        domain = domain[:-1]  # Remove the trailing dot
    hostname_part = domain.split(".")
    if not hostname_part or re.match(r"[0-9]+$", hostname_part[-1]):
        return False  # Reject if TLD is numeric or hostname part is missing
    regex = re.compile(r"(?!-)[A-Z0-9-]{1,63}(?<!-)$", re.IGNORECASE)
    return all(regex.match(label) for label in hostname_part)


# Read domains from file
domains_file = sys.argv[1]
try:
    with open(domains_file, 'r') as file:
        domains = [line.strip() for line in file if validate_domain_name(line.strip())]
except FileNotFoundError:
    sys.stderr.write(f"Error: The file {domains_file} was not found\n")
    exit(1)




# Function to perform NS lookup and AXFR
def perform_zone_transfer(domain):
    hostname = dns.name.from_text(domain)
    
    # Function to attempt AXFR using both UDP and TCP
    def attempt_axfr(server, hostname, use_tcp=False):
        try:
            if use_tcp:
                axfr_query = dns.query.tcp(dns.message.make_query(hostname, dns.rdatatype.AXFR), server)
            else:
                axfr_query = dns.query.xfr(server, hostname)
            zone = dns.zone.from_xfr(axfr_query)
            print(f"AXFR successful for {domain} with server {server} {'using TCP' if use_tcp else 'using UDP'}")
            for name, node in zone.nodes.items():
                print(node.to_text(name))
        except Exception as e:
            print(f"AXFR failed for {domain} with server {server} {'using TCP' if use_tcp else 'using UDP'}: {e}")
    
    # Always try AXFR on the base domain with UDP first
    attempt_axfr(domain, hostname)

    # Then try with TCP on the base domain
    attempt_axfr(domain, hostname, use_tcp=True)

    # Search for NS records and attempt AXFR with each NS server
    try:
        ns_servers = dns.resolver.query(hostname, 'NS')
        for ns in ns_servers:
            server = ns.to_text()
            # Try AXFR with UDP
            attempt_axfr(server, hostname)
            # Try AXFR with TCP
            attempt_axfr(server, hostname, use_tcp=True)
    except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer):
        print(f"No NS records found for {domain}. AXFR attempts were made on the base domain.")

# Main loop to process each domain
for domain in domains:
    print(f"Processing domain: {domain}")
    perform_zone_transfer(domain)
