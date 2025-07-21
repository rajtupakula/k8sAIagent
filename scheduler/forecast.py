import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error
import json
import os

class ResourceForecaster:
    """Forecast resource usage and provide pod placement recommendations."""
    
    def __init__(self, data_path: str = "./forecast_data"):
        self.logger = logging.getLogger(__name__)
        self.data_path = data_path
        self.models = {}
        self.latest_forecast = None
        self.historical_data = {}
        self.placement_recommendations = []
        
        # Ensure data directory exists
        os.makedirs(data_path, exist_ok=True)
        
        # Load historical data if available
        self._load_historical_data()
        
        # Initialize models
        self._initialize_models()
    
    def _load_historical_data(self):
        """Load historical resource usage data."""
        try:
            data_file = os.path.join(self.data_path, "historical_data.json")
            if os.path.exists(data_file):
                with open(data_file, 'r') as f:
                    self.historical_data = json.load(f)
                self.logger.info(f"Loaded historical data with {len(self.historical_data)} entries")
            else:
                self.historical_data = {
                    "cpu_usage": [],
                    "memory_usage": [],
                    "storage_usage": [],
                    "timestamps": [],
                    "node_metrics": {},
                    "pod_metrics": {}
                }
                self._generate_sample_data()
        except Exception as e:
            self.logger.error(f"Error loading historical data: {e}")
            self.historical_data = {}
    
    def _save_historical_data(self):
        """Save historical data to disk."""
        try:
            data_file = os.path.join(self.data_path, "historical_data.json")
            with open(data_file, 'w') as f:
                json.dump(self.historical_data, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving historical data: {e}")
    
    def _generate_sample_data(self):
        """Generate sample historical data for demonstration."""
        base_time = datetime.now() - timedelta(days=30)
        
        # Generate 30 days of hourly data
        for i in range(30 * 24):
            timestamp = base_time + timedelta(hours=i)
            
            # Simulate realistic usage patterns with daily/weekly cycles
            hour_of_day = timestamp.hour
            day_of_week = timestamp.weekday()
            
            # Business hours pattern (higher usage 9-17 on weekdays)
            business_factor = 1.0
            if day_of_week < 5:  # Weekday
                if 9 <= hour_of_day <= 17:
                    business_factor = 1.5
                elif 6 <= hour_of_day <= 21:
                    business_factor = 1.2
            else:  # Weekend
                business_factor = 0.7
            
            # Add some randomness
            random_factor = np.random.normal(1.0, 0.1)
            
            cpu_usage = min(95, max(5, 30 * business_factor * random_factor))
            memory_usage = min(90, max(10, 40 * business_factor * random_factor))
            storage_usage = min(85, max(15, 25 + (i / (30 * 24)) * 10))  # Gradual increase
            
            self.historical_data["timestamps"].append(timestamp.isoformat())
            self.historical_data["cpu_usage"].append(cpu_usage)
            self.historical_data["memory_usage"].append(memory_usage)
            self.historical_data["storage_usage"].append(storage_usage)
        
        # Generate node-specific data
        nodes = ["worker-1", "worker-2", "worker-3", "master-1"]
        for node in nodes:
            self.historical_data["node_metrics"][node] = {
                "cpu_capacity": np.random.uniform(4, 16),  # CPU cores
                "memory_capacity": np.random.uniform(8, 64),  # GB
                "current_cpu": np.random.uniform(20, 80),  # % usage
                "current_memory": np.random.uniform(30, 70),  # % usage
                "pod_count": np.random.randint(5, 25),
                "labels": {
                    "node-type": np.random.choice(["worker", "master"]),
                    "zone": np.random.choice(["us-west-1a", "us-west-1b", "us-west-1c"])
                }
            }
        
        self._save_historical_data()
        self.logger.info("Generated sample historical data")
    
    def _initialize_models(self):
        """Initialize forecasting models."""
        try:
            # Random Forest models for different resource types
            self.models = {
                "cpu": RandomForestRegressor(n_estimators=100, random_state=42),
                "memory": RandomForestRegressor(n_estimators=100, random_state=42),
                "storage": RandomForestRegressor(n_estimators=100, random_state=42)
            }
            
            # Train models if we have enough data
            if len(self.historical_data.get("timestamps", [])) > 24:  # At least 24 hours of data
                self._train_models()
            
            self.logger.info("Initialized forecasting models")
            
        except Exception as e:
            self.logger.error(f"Error initializing models: {e}")
    
    def _train_models(self):
        """Train the forecasting models with historical data."""
        try:
            if not self.historical_data or len(self.historical_data["timestamps"]) < 24:
                self.logger.warning("Insufficient data to train models")
                return
            
            # Prepare features and targets
            features, targets = self._prepare_training_data()
            
            if len(features) < 10:  # Need minimum samples
                self.logger.warning("Insufficient training samples")
                return
            
            # Train each model
            for resource_type in ["cpu", "memory", "storage"]:
                if resource_type in targets:
                    y = targets[resource_type]
                    self.models[resource_type].fit(features, y)
                    
                    # Calculate training accuracy
                    predictions = self.models[resource_type].predict(features)
                    mae = mean_absolute_error(y, predictions)
                    self.logger.info(f"Trained {resource_type} model, MAE: {mae:.2f}")
            
        except Exception as e:
            self.logger.error(f"Error training models: {e}")
    
    def _prepare_training_data(self) -> Tuple[np.ndarray, Dict[str, np.ndarray]]:
        """Prepare features and targets for model training."""
        timestamps = [datetime.fromisoformat(ts) for ts in self.historical_data["timestamps"]]
        
        features = []
        for ts in timestamps:
            # Time-based features
            feature_vector = [
                ts.hour,  # Hour of day (0-23)
                ts.weekday(),  # Day of week (0-6)
                ts.day,  # Day of month (1-31)
                ts.month,  # Month (1-12)
                # Add more sophisticated features
                np.sin(2 * np.pi * ts.hour / 24),  # Cyclical hour
                np.cos(2 * np.pi * ts.hour / 24),
                np.sin(2 * np.pi * ts.weekday() / 7),  # Cyclical day of week
                np.cos(2 * np.pi * ts.weekday() / 7),
            ]
            features.append(feature_vector)
        
        features = np.array(features)
        
        targets = {
            "cpu": np.array(self.historical_data["cpu_usage"]),
            "memory": np.array(self.historical_data["memory_usage"]),
            "storage": np.array(self.historical_data["storage_usage"])
        }
        
        return features, targets
    
    def generate_forecast(self, days: int, resource_type: str) -> Dict[str, Any]:
        """Generate forecast for specified days and resource type."""
        try:
            if resource_type.lower() not in self.models:
                return {"error": f"Unknown resource type: {resource_type}"}
            
            model = self.models[resource_type.lower()]
            
            # Generate future timestamps
            start_time = datetime.now()
            future_timestamps = []
            future_features = []
            
            for hour in range(days * 24):
                future_time = start_time + timedelta(hours=hour)
                future_timestamps.append(future_time)
                
                # Prepare features for this timestamp
                feature_vector = [
                    future_time.hour,
                    future_time.weekday(),
                    future_time.day,
                    future_time.month,
                    np.sin(2 * np.pi * future_time.hour / 24),
                    np.cos(2 * np.pi * future_time.hour / 24),
                    np.sin(2 * np.pi * future_time.weekday() / 7),
                    np.cos(2 * np.pi * future_time.weekday() / 7),
                ]
                future_features.append(feature_vector)
            
            # Make predictions
            future_features = np.array(future_features)
            predictions = model.predict(future_features)
            
            # Prepare forecast data
            forecast_data = []
            for i, (timestamp, value) in enumerate(zip(future_timestamps, predictions)):
                forecast_data.append({
                    "timestamp": timestamp.isoformat(),
                    "value": max(0, min(100, value)),  # Clamp between 0-100%
                    "type": "forecast"
                })
            
            # Add recent historical data for context
            historical_context = []
            recent_timestamps = self.historical_data["timestamps"][-48:]  # Last 48 hours
            recent_values = self.historical_data[f"{resource_type.lower()}_usage"][-48:]
            
            for ts, val in zip(recent_timestamps, recent_values):
                historical_context.append({
                    "timestamp": ts,
                    "value": val,
                    "type": "historical"
                })
            
            self.latest_forecast = historical_context + forecast_data
            
            # Generate insights
            insights = self._generate_forecast_insights(predictions, resource_type)
            
            result = {
                "resource_type": resource_type,
                "forecast_days": days,
                "data": self.latest_forecast,
                "insights": insights,
                "generated_at": datetime.now().isoformat()
            }
            
            # Save forecast
            self._save_forecast(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error generating forecast: {e}")
            return {"error": str(e)}
    
    def _generate_forecast_insights(self, predictions: np.ndarray, resource_type: str) -> Dict[str, Any]:
        """Generate insights from forecast predictions."""
        insights = {
            "max_usage": float(np.max(predictions)),
            "min_usage": float(np.min(predictions)),
            "avg_usage": float(np.mean(predictions)),
            "peak_hours": [],
            "recommendations": []
        }
        
        # Find peak usage periods
        threshold = np.percentile(predictions, 90)  # Top 10% usage
        peak_indices = np.where(predictions >= threshold)[0]
        
        # Group consecutive peak hours
        peak_periods = []
        if len(peak_indices) > 0:
            current_period_start = peak_indices[0]
            current_period_end = peak_indices[0]
            
            for i in range(1, len(peak_indices)):
                if peak_indices[i] == current_period_end + 1:
                    current_period_end = peak_indices[i]
                else:
                    peak_periods.append((current_period_start, current_period_end))
                    current_period_start = peak_indices[i]
                    current_period_end = peak_indices[i]
            
            peak_periods.append((current_period_start, current_period_end))
        
        insights["peak_periods"] = peak_periods
        
        # Generate recommendations
        if insights["max_usage"] > 85:
            insights["recommendations"].append(
                f"High {resource_type} usage predicted (>85%). Consider scaling up resources."
            )
        
        if len(peak_periods) > 0:
            insights["recommendations"].append(
                f"Peak {resource_type} usage expected during {len(peak_periods)} periods. "
                "Consider pre-scaling or load balancing."
            )
        
        if insights["avg_usage"] < 30:
            insights["recommendations"].append(
                f"Low average {resource_type} usage predicted. Consider optimizing resource allocation."
            )
        
        return insights
    
    def get_latest_forecast(self) -> Optional[List[Dict[str, Any]]]:
        """Get the latest forecast data."""
        return self.latest_forecast
    
    def get_placement_recommendations(self) -> List[Dict[str, Any]]:
        """Get pod placement recommendations based on current cluster state."""
        try:
            # Simulate pod placement analysis
            recommendations = []
            
            # Mock current pods that could be optimized
            mock_pods = [
                {
                    "name": "web-app-1",
                    "current_node": "worker-1", 
                    "cpu_request": 500,  # millicores
                    "memory_request": 1024,  # MB
                    "namespace": "default"
                },
                {
                    "name": "database-pod",
                    "current_node": "worker-2",
                    "cpu_request": 1000,
                    "memory_request": 2048,
                    "namespace": "production"
                },
                {
                    "name": "cache-service",
                    "current_node": "worker-1",
                    "cpu_request": 200,
                    "memory_request": 512,
                    "namespace": "default"
                }
            ]
            
            # Analyze each pod for better placement
            for pod in mock_pods:
                recommendation = self._analyze_pod_placement(pod)
                if recommendation:
                    recommendations.append(recommendation)
            
            self.placement_recommendations = recommendations
            return recommendations
            
        except Exception as e:
            self.logger.error(f"Error generating placement recommendations: {e}")
            return []
    
    def _analyze_pod_placement(self, pod: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze optimal placement for a specific pod."""
        current_node = pod["current_node"]
        
        # Get node metrics
        node_metrics = self.historical_data.get("node_metrics", {})
        
        if current_node not in node_metrics:
            return None
        
        current_node_metrics = node_metrics[current_node]
        
        # Find better node based on resource availability and utilization
        best_node = None
        best_score = -1
        
        for node_name, metrics in node_metrics.items():
            if node_name == current_node:
                continue
            
            # Calculate placement score based on:
            # 1. Available resources
            # 2. Current utilization
            # 3. Node labels/affinity (simplified)
            
            cpu_available = (100 - metrics["current_cpu"]) / 100
            memory_available = (100 - metrics["current_memory"]) / 100
            
            # Simple scoring algorithm
            score = (cpu_available * 0.4 + memory_available * 0.4 + 
                    (1 - metrics["pod_count"] / 30) * 0.2)  # Pod density factor
            
            if score > best_score:
                best_score = score
                best_node = node_name
        
        # Only recommend if there's a significant improvement
        current_score = ((100 - current_node_metrics["current_cpu"]) / 100 * 0.4 +
                        (100 - current_node_metrics["current_memory"]) / 100 * 0.4 +
                        (1 - current_node_metrics["pod_count"] / 30) * 0.2)
        
        if best_node and best_score > current_score + 0.1:  # At least 10% improvement
            improvement_pct = ((best_score - current_score) / current_score) * 100
            
            return {
                "pod_name": f"{pod['namespace']}/{pod['name']}",
                "current_node": current_node,
                "recommended_node": best_node,
                "reason": f"Better resource availability and lower utilization",
                "improvement": f"{improvement_pct:.1f}% better placement score",
                "current_score": f"{current_score:.2f}",
                "recommended_score": f"{best_score:.2f}"
            }
        
        return None
    
    def add_metrics_data(self, metrics: Dict[str, Any]):
        """Add new metrics data to historical dataset."""
        try:
            timestamp = datetime.now().isoformat()
            
            self.historical_data["timestamps"].append(timestamp)
            self.historical_data["cpu_usage"].append(metrics.get("cpu_usage", 0))
            self.historical_data["memory_usage"].append(metrics.get("memory_usage", 0))
            self.historical_data["storage_usage"].append(metrics.get("storage_usage", 0))
            
            # Keep only last 30 days of data (720 hours)
            max_entries = 720
            if len(self.historical_data["timestamps"]) > max_entries:
                for key in ["timestamps", "cpu_usage", "memory_usage", "storage_usage"]:
                    self.historical_data[key] = self.historical_data[key][-max_entries:]
            
            # Update node metrics if provided
            if "node_metrics" in metrics:
                self.historical_data["node_metrics"].update(metrics["node_metrics"])
            
            # Retrain models periodically (every 24 new data points)
            if len(self.historical_data["timestamps"]) % 24 == 0:
                self._train_models()
            
            # Save updated data
            self._save_historical_data()
            
        except Exception as e:
            self.logger.error(f"Error adding metrics data: {e}")
    
    def _save_forecast(self, forecast: Dict[str, Any]):
        """Save forecast to disk."""
        try:
            forecast_file = os.path.join(self.data_path, "latest_forecast.json")
            with open(forecast_file, 'w') as f:
                json.dump(forecast, f, indent=2)
        except Exception as e:
            self.logger.error(f"Error saving forecast: {e}")
    
    def get_model_performance(self) -> Dict[str, Any]:
        """Get performance metrics for the forecasting models."""
        performance = {}
        
        try:
            if len(self.historical_data.get("timestamps", [])) < 48:
                return {"error": "Insufficient data for performance evaluation"}
            
            # Use last 48 hours for validation
            features, targets = self._prepare_training_data()
            
            if len(features) < 48:
                return {"error": "Insufficient training data"}
            
            # Split data: train on all but last 24, test on last 24
            split_point = -24
            train_features, test_features = features[:split_point], features[split_point:]
            
            for resource_type in ["cpu", "memory", "storage"]:
                if resource_type in targets:
                    train_targets = targets[resource_type][:split_point]
                    test_targets = targets[resource_type][split_point:]
                    
                    # Train model on training data
                    temp_model = RandomForestRegressor(n_estimators=100, random_state=42)
                    temp_model.fit(train_features, train_targets)
                    
                    # Test on validation data
                    predictions = temp_model.predict(test_features)
                    mae = mean_absolute_error(test_targets, predictions)
                    mape = np.mean(np.abs((test_targets - predictions) / np.maximum(test_targets, 1))) * 100
                    
                    performance[resource_type] = {
                        "mae": float(mae),
                        "mape": float(mape),
                        "accuracy": max(0, 100 - mape)  # Simple accuracy metric
                    }
            
        except Exception as e:
            self.logger.error(f"Error calculating model performance: {e}")
            return {"error": str(e)}
        
        return performance
    
    def optimize_cluster_resources(self) -> Dict[str, Any]:
        """Provide cluster-wide resource optimization recommendations."""
        try:
            recommendations = []
            
            # Analyze overall cluster utilization
            if self.historical_data:
                recent_cpu = np.mean(self.historical_data["cpu_usage"][-24:])  # Last 24 hours
                recent_memory = np.mean(self.historical_data["memory_usage"][-24:])
                recent_storage = np.mean(self.historical_data["storage_usage"][-24:])
                
                # CPU recommendations
                if recent_cpu < 30:
                    recommendations.append({
                        "type": "scale_down",
                        "resource": "CPU",
                        "current_usage": f"{recent_cpu:.1f}%",
                        "recommendation": "Consider reducing CPU requests or scaling down replicas",
                        "potential_savings": "20-30% cost reduction"
                    })
                elif recent_cpu > 80:
                    recommendations.append({
                        "type": "scale_up",
                        "resource": "CPU", 
                        "current_usage": f"{recent_cpu:.1f}%",
                        "recommendation": "Consider adding nodes or increasing CPU limits",
                        "urgency": "high"
                    })
                
                # Memory recommendations
                if recent_memory < 40:
                    recommendations.append({
                        "type": "optimize",
                        "resource": "Memory",
                        "current_usage": f"{recent_memory:.1f}%",
                        "recommendation": "Memory is underutilized. Review memory requests and limits",
                        "potential_savings": "15-25% cost reduction"
                    })
                elif recent_memory > 85:
                    recommendations.append({
                        "type": "scale_up",
                        "resource": "Memory",
                        "current_usage": f"{recent_memory:.1f}%", 
                        "recommendation": "Memory pressure detected. Consider adding memory or nodes",
                        "urgency": "medium"
                    })
                
                # Storage recommendations
                if recent_storage > 75:
                    recommendations.append({
                        "type": "cleanup",
                        "resource": "Storage",
                        "current_usage": f"{recent_storage:.1f}%",
                        "recommendation": "Storage usage is high. Consider cleanup or expansion",
                        "urgency": "medium"
                    })
            
            return {
                "recommendations": recommendations,
                "generated_at": datetime.now().isoformat(),
                "cluster_efficiency_score": self._calculate_efficiency_score()
            }
            
        except Exception as e:
            self.logger.error(f"Error optimizing cluster resources: {e}")
            return {"error": str(e)}
    
    def _calculate_efficiency_score(self) -> float:
        """Calculate overall cluster efficiency score (0-100)."""
        try:
            if not self.historical_data or len(self.historical_data["timestamps"]) < 24:
                return 50.0  # Default score
            
            # Get recent averages
            recent_cpu = np.mean(self.historical_data["cpu_usage"][-24:])
            recent_memory = np.mean(self.historical_data["memory_usage"][-24:])
            
            # Optimal utilization is around 60-70%
            optimal_range = (60, 70)
            
            def score_utilization(usage):
                if optimal_range[0] <= usage <= optimal_range[1]:
                    return 100
                elif usage < optimal_range[0]:
                    # Underutilization penalty
                    return max(0, 100 - (optimal_range[0] - usage) * 2)
                else:
                    # Overutilization penalty
                    return max(0, 100 - (usage - optimal_range[1]) * 3)
            
            cpu_score = score_utilization(recent_cpu)
            memory_score = score_utilization(recent_memory)
            
            # Weighted average (CPU slightly more important)
            efficiency_score = (cpu_score * 0.6 + memory_score * 0.4)
            
            return round(efficiency_score, 1)
            
        except Exception as e:
            self.logger.error(f"Error calculating efficiency score: {e}")
            return 50.0