# Content-Distribution
add node4 to node3:
    addneighbor uuid=686f60-1939-4d62-860c-4c703d7a67a6 host=127.0.0.1 backend_port=18349 metric=15

add node3 to node4:
    addneighbor uuid=3d2f4e34-6d21-4dda-aa78-796e3507903c host=127.0.0.1 backend_port=18348 metric=15

add node3 to node2:
    addneighbor uuid=3d2f4e34-6d21-4dda-aa78-796e3507903c host=127.0.0.1 backend_port=18348 metric=5
    
add node2 to node3:
    addneighbor uuid=24f22a83-16f4-4bd5-af63-9b5c6e979dbb host=127.0.0.1 backend_port=18347 metric=5