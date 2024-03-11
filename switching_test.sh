#!/bin/bash
curl -X GET "http://localhost:5000/api/set_all?signal=FFFFFFFFFFFFFFFF"
sleep(1)
curl -X GET "http://localhost:5000/api/set_all?signal=CAFFFFFFFFFFFFFF"
curl -X GET "http://localhost:5000/api/set_all?signal=FFCAFFFFFFFFFFFF"
