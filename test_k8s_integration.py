#!/usr/bin/env python3
"""
Test script to verify Kubernetes integration works correctly
"""

import sys
import os

# Add the current directory to the path so we can import from complete_expert_dashboard
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from complete_expert_dashboard import (
        get_real_cluster_info,
        get_real_pod_status, 
        get_real_node_status,
        get_real_events,
        get_real_resource_usage,
        calculate_cluster_health_score
    )
    
    print("✅ Successfully imported Kubernetes functions")
    
    # Test cluster connection
    print("\n🔍 Testing cluster connection...")
    cluster_info = get_real_cluster_info()
    print(f"Cluster Status: {cluster_info['status']}")
    print(f"Message: {cluster_info['message']}")
    print(f"Nodes: {cluster_info['nodes']}")
    print(f"Pods: {cluster_info['pods']}")
    
    if cluster_info['status'] == 'connected':
        print("✅ Kubernetes connection successful!")
        
        # Test pod data
        print("\n🚀 Testing pod data retrieval...")
        pods = get_real_pod_status()
        print(f"Found {len(pods)} pods")
        if pods:
            print(f"Sample pod: {pods[0]['name']} - Status: {pods[0]['status']}")
        
        # Test node data  
        print("\n🖥️ Testing node data retrieval...")
        nodes = get_real_node_status()
        print(f"Found {len(nodes)} nodes")
        if nodes:
            print(f"Sample node: {nodes[0]['name']} - Status: {nodes[0]['status']}")
        
        # Test events
        print("\n📊 Testing events retrieval...")
        events = get_real_events()
        print(f"Found {len(events)} recent events")
        if events:
            print(f"Latest event: {events[0]['reason']} - Type: {events[0]['type']}")
        
        # Test metrics
        print("\n📈 Testing metrics retrieval...")
        metrics = get_real_resource_usage()
        print(f"CPU data points: {len(metrics['cpu_usage'])}")
        print(f"Memory data points: {len(metrics['memory_usage'])}")
        
        # Test health score
        print("\n🏥 Testing health score calculation...")
        health_score = calculate_cluster_health_score()
        print(f"Cluster health score: {health_score}%")
        
        print("\n🎉 All tests passed! Real Kubernetes integration is working.")
        
    else:
        print(f"⚠️ Kubernetes connection failed: {cluster_info['message']}")
        print("Dashboard will show connection status and allow retry.")
        
except Exception as e:
    print(f"❌ Error testing Kubernetes integration: {str(e)}")
    import traceback
    traceback.print_exc()
