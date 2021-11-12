{
  "account": "Verisign",
  "api_rectify": false,
  "dnssec": false,
  "id": "testing.com.",
  "kind": "Master",
  "last_check": 0,
  "masters": [],
  "name": "testing.com.",
  "notified_serial": 2018061201,
  "nsec3narrow": false,
  "nsec3param": "",
  "rrsets": [
    {
      "comments": [],
      "name": "www.testing.com.",
      "records": [
        {
          "content": "217.66.55.28",
          "disabled": false
        }
      ],
      "ttl": 3600,
      "type": "A"
    },
    {
      "comments": [
        {
          "account": "frank.brehm",
          "content": "local",
          "modified_at": 1518186464
        }
      ],
      "name": "local.testing.com.",
      "records": [
        {
          "content": "ns1-local.example.com.",
          "disabled": false
        },
        {
          "content": "ns2-local.example.com.",
          "disabled": false
        },
        {
          "content": "ns3-local.example.com.",
          "disabled": false
        }
      ],
      "ttl": 3600,
      "type": "NS"
    },
    {
      "comments": [],
      "name": "live.testing.com.",
      "records": [
        {
          "content": "www.testing.com.",
          "disabled": false
        }
      ],
      "ttl": 3600,
      "type": "CNAME"
    },
    {
      "comments": [
        {
          "account": "frank.brehm",
          "content": "",
          "modified_at": 1520325479
        }
      ],
      "name": "web02.testing.com.",
      "records": [
        {
          "content": "217.66.55.28",
          "disabled": true
        }
      ],
      "ttl": 3600,
      "type": "A"
    },
    {
      "comments": [],
      "name": "testing.com.",
      "records": [
        {
          "content": "10 mx01.example.com.",
          "disabled": false
        },
        {
          "content": "10 mx02.example.com.",
          "disabled": false
        }
      ],
      "ttl": 3600,
      "type": "MX"
    },
    {
      "comments": [],
      "name": "testing.com.",
      "records": [
        {
          "content": "ns1.example.com. hostmaster.example.com. 2018061201 10800 1800 604800 3600",
          "disabled": false
        }
      ],
      "ttl": 3600,
      "type": "SOA"
    },
    {
      "comments": [],
      "name": "testing.com.",
      "records": [
        {
          "content": "ns3.example.com.",
          "disabled": false
        },
        {
          "content": "ns1.example.com.",
          "disabled": false
        },
        {
          "content": "ns2.example.com.",
          "disabled": false
        }
      ],
      "ttl": 3600,
      "type": "NS"
    }
  ],
  "serial": 2018061201,
  "soa_edit": "",
  "soa_edit_api": "INCEPTION-INCREMENT",
  "url": "/api/v1/servers/localhost/zones/testing.com."
}
