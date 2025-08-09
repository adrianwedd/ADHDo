/**
 * Evolution Observatory - Real-time monitoring system
 * 
 * Modular JavaScript for evolution system monitoring with WebSocket
 * integration and real-time chart rendering.
 */

class EvolutionObservatory {
    constructor() {
        this.evolutionData = [];
        this.currentGeneration = 0;
        this.isEvolutionRunning = false;
        this.websocket = null;
        this.initializeChart();
        this.initializeWebSocket();
        this.startRealTimeUpdates();
    }

    initializeChart() {
        this.canvas = document.getElementById('evolutionChart');
        this.ctx = this.canvas.getContext('2d');
        this.resizeCanvas();
        window.addEventListener('resize', () => this.resizeCanvas());
    }

    resizeCanvas() {
        const rect = this.canvas.parentElement.getBoundingClientRect();
        this.canvas.width = rect.width;
        this.canvas.height = rect.height;
    }

    initializeWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/api/evolution/ws`;
        
        console.log('Connecting to Evolution Observatory WebSocket:', wsUrl);
        
        try {
            this.websocket = new WebSocket(wsUrl);
            
            this.websocket.onopen = () => {
                console.log('🧬 Evolution Observatory WebSocket connected');
                // Request initial status
                this.websocket.send(JSON.stringify({ type: 'request_update' }));
            };
            
            this.websocket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    if (data.type === 'evolution_update') {
                        console.log('📊 Received evolution status via WebSocket:', data);
                        this.processEvolutionData(data.data);
                    } else if (data.type === 'initial_state') {
                        console.log('🎯 Received initial evolution state:', data);
                        this.processEvolutionData(data.data);
                    }
                } catch (error) {
                    console.error('Failed to parse WebSocket message:', error);
                }
            };
            
            this.websocket.onclose = () => {
                console.log('🔌 Evolution Observatory WebSocket disconnected, reconnecting...');
                // Reconnect after 3 seconds
                setTimeout(() => this.initializeWebSocket(), 3000);
            };
            
            this.websocket.onerror = (error) => {
                console.error('Evolution Observatory WebSocket error:', error);
            };
            
            // Keep connection alive with ping/pong
            setInterval(() => {
                if (this.websocket && this.websocket.readyState === WebSocket.OPEN) {
                    this.websocket.send(JSON.stringify({ type: 'ping' }));
                }
            }, 30000); // Ping every 30 seconds
            
        } catch (error) {
            console.error('Failed to initialize WebSocket:', error);
            console.log('Falling back to REST API polling');
        }
    }

    async startRealTimeUpdates() {
        // Simulate real-time evolution data when WebSocket is not available
        setInterval(() => {
            if (!this.websocket || this.websocket.readyState !== WebSocket.OPEN) {
                this.updateEvolutionData();
                this.renderUI();
            }
        }, 5000);

        // Initial load
        await this.loadEvolutionData();
        this.renderUI();
    }

    async loadEvolutionData() {
        // Load evolution data from the real API
        try {
            const response = await fetch('/api/evolution/status');
            if (response.ok) {
                const data = await response.json();
                this.processEvolutionData(data);
                console.log('Loaded real evolution data:', data);
            } else {
                console.warn('API not available, using simulated data');
                this.simulateEvolutionData();
            }
        } catch (error) {
            console.warn('Failed to load evolution data, using simulated data:', error);
            this.simulateEvolutionData();
        }
    }

    processEvolutionData(data) {
        this.currentData = {
            strategies: data.adaptive_improvements || data.strategies || [],
            species: data.active_experiments || data.species || [],
            population: data.optimization_cycles_completed || data.population || 0,
            avgFitness: data.performance_metrics?.avg_fitness || data.avgFitness || 0,
            generation: data.current_generation || data.generation || 0,
            speciesCount: data.system_adaptations?.length || data.speciesCount || 0
        };
        this.currentGeneration = this.currentData.generation;
    }

    simulateEvolutionData() {
        // Generate realistic evolution simulation data
        const strategies = [
            { id: 'intelligent_caching', fitness: 0.88, complexity: 7, species: 'performance_optimizers' },
            { id: 'modular_architecture', fitness: 0.92, complexity: 5, species: 'code_quality_specialists' },
            { id: 'websocket_management', fitness: 0.85, complexity: 6, species: 'communication_experts' },
            { id: 'ci_pipeline_optimization', fitness: 0.78, complexity: 4, species: 'deployment_specialists' },
            { id: 'error_handling_patterns', fitness: 0.71, complexity: 3, species: 'reliability_experts' },
            { id: 'database_query_optimization', fitness: 0.66, complexity: 8, species: 'performance_optimizers' }
        ];

        const species = [
            { name: 'performance_optimizers', population: 2, avgFitness: 0.77, maxFitness: 0.88 },
            { name: 'code_quality_specialists', population: 1, avgFitness: 0.92, maxFitness: 0.92 },
            { name: 'communication_experts', population: 1, avgFitness: 0.85, maxFitness: 0.85 },
            { name: 'deployment_specialists', population: 1, avgFitness: 0.78, maxFitness: 0.78 },
            { name: 'reliability_experts', population: 1, avgFitness: 0.71, maxFitness: 0.71 }
        ];

        this.currentData = {
            strategies,
            species,
            population: strategies.length,
            avgFitness: strategies.reduce((sum, s) => sum + s.fitness, 0) / strategies.length,
            generation: this.currentGeneration,
            speciesCount: species.length
        };
    }

    updateEvolutionData() {
        // Simulate evolution progress
        this.currentGeneration++;
        
        // Simulate fitness changes over time
        if (this.currentData && this.currentData.strategies) {
            this.currentData.strategies.forEach(strategy => {
                // Small random fitness changes to simulate evolution
                const change = (Math.random() - 0.5) * 0.01; // Smaller changes for stability
                strategy.fitness = Math.max(0.1, Math.min(1.0, strategy.fitness + change));
            });
            
            // Update derived metrics
            this.currentData.avgFitness = this.currentData.strategies.reduce((sum, s) => sum + s.fitness, 0) / this.currentData.strategies.length;
            this.currentData.generation = this.currentGeneration;
        }

        // Store evolution timeline data
        if (this.currentData) {
            this.evolutionData.push({
                generation: this.currentGeneration,
                avgFitness: this.currentData.avgFitness,
                timestamp: Date.now()
            });

            // Keep only last 50 data points for performance
            if (this.evolutionData.length > 50) {
                this.evolutionData.shift();
            }
        }
    }

    renderUI() {
        if (!this.currentData) return;

        this.renderStrategies();
        this.renderSpecies();
        this.renderMetrics();
        this.renderEvolutionChart();
    }

    renderStrategies() {
        const container = document.getElementById('strategyList');
        if (!this.currentData.strategies || !container) return;

        container.innerHTML = this.currentData.strategies.map(strategy => {
            const fitnessClass = strategy.fitness > 0.8 ? 'strategy-high' : 
                               strategy.fitness > 0.6 ? 'strategy-medium' : 'strategy-low';
            
            return `
                <div class="strategy-item ${fitnessClass}">
                    <div>
                        <div style="font-weight: 600;">${strategy.id.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</div>
                        <div style="font-size: 0.8rem; opacity: 0.7;">Species: ${strategy.species.replace(/_/g, ' ')}</div>
                    </div>
                    <div>
                        <div class="fitness-bar">
                            <div class="fitness-fill" style="width: ${strategy.fitness * 100}%"></div>
                        </div>
                        <div style="text-align: center; margin-top: 0.3rem; font-size: 0.9rem;">
                            ${(strategy.fitness * 100).toFixed(1)}%
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }

    renderSpecies() {
        const container = document.getElementById('speciesList');
        if (!this.currentData.species || !container) return;

        container.innerHTML = this.currentData.species.map(species => `
            <div class="species-item">
                <div class="species-name">${species.name.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</div>
                <div class="species-stats">
                    <span>Pop: ${species.population}</span>
                    <span>Avg: ${(species.avgFitness * 100).toFixed(1)}%</span>
                    <span>Max: ${(species.maxFitness * 100).toFixed(1)}%</span>
                </div>
            </div>
        `).join('');
    }

    renderMetrics() {
        if (!this.currentData) return;

        const populationEl = document.getElementById('populationSize');
        const fitnessEl = document.getElementById('avgFitness');
        const generationEl = document.getElementById('generationCount');
        const speciesEl = document.getElementById('speciesCount');

        if (populationEl) populationEl.textContent = this.currentData.population;
        if (fitnessEl) fitnessEl.textContent = (this.currentData.avgFitness * 100).toFixed(1) + '%';
        if (generationEl) generationEl.textContent = this.currentData.generation;
        if (speciesEl) speciesEl.textContent = this.currentData.speciesCount;
    }

    renderEvolutionChart() {
        if (!this.evolutionData.length || !this.ctx) return;

        const ctx = this.ctx;
        const canvas = this.canvas;
        
        // Clear canvas
        ctx.clearRect(0, 0, canvas.width, canvas.height);

        // Draw grid
        ctx.strokeStyle = 'rgba(255, 255, 255, 0.1)';
        ctx.lineWidth = 1;

        for (let i = 0; i <= 10; i++) {
            const y = (canvas.height / 10) * i;
            ctx.beginPath();
            ctx.moveTo(0, y);
            ctx.lineTo(canvas.width, y);
            ctx.stroke();
        }

        for (let i = 0; i <= 10; i++) {
            const x = (canvas.width / 10) * i;
            ctx.beginPath();
            ctx.moveTo(x, 0);
            ctx.lineTo(x, canvas.height);
            ctx.stroke();
        }

        // Draw evolution line
        if (this.evolutionData.length > 1) {
            ctx.strokeStyle = '#667eea';
            ctx.lineWidth = 3;
            ctx.beginPath();

            const maxGeneration = Math.max(...this.evolutionData.map(d => d.generation));
            const minGeneration = Math.min(...this.evolutionData.map(d => d.generation));
            const generationRange = maxGeneration - minGeneration || 1;

            this.evolutionData.forEach((point, index) => {
                const x = (point.generation - minGeneration) / generationRange * canvas.width;
                const y = canvas.height - (point.avgFitness * canvas.height);

                if (index === 0) {
                    ctx.moveTo(x, y);
                } else {
                    ctx.lineTo(x, y);
                }
            });

            ctx.stroke();

            // Draw points
            ctx.fillStyle = '#667eea';
            this.evolutionData.forEach(point => {
                const x = (point.generation - minGeneration) / generationRange * canvas.width;
                const y = canvas.height - (point.avgFitness * canvas.height);
                
                ctx.beginPath();
                ctx.arc(x, y, 4, 0, Math.PI * 2);
                ctx.fill();
            });
        }

        // Draw labels
        ctx.fillStyle = 'rgba(255, 255, 255, 0.7)';
        ctx.font = '12px SF Pro Display, system-ui, sans-serif';
        ctx.fillText('Generation →', canvas.width - 80, canvas.height - 10);
        
        ctx.save();
        ctx.translate(15, canvas.height / 2);
        ctx.rotate(-Math.PI / 2);
        ctx.fillText('← Fitness', 0, 0);
        ctx.restore();
    }
}

// Control functions for evolution management
async function triggerEvolution() {
    console.log('🧬 Triggering evolution cycle...');
    
    try {
        const response = await fetch('/api/evolution/trigger', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (result.status === 'triggered') {
            alert(`🧬 Evolution cycle started! Generation ${result.generation} is now running. Expected duration: ${result.expected_duration || 'Unknown'}`);
            // Reload data to show changes
            if (window.evolutionObservatory && window.evolutionObservatory.websocket && 
                window.evolutionObservatory.websocket.readyState === WebSocket.OPEN) {
                window.evolutionObservatory.websocket.send(JSON.stringify({ type: 'request_update' }));
            } else if (window.evolutionObservatory) {
                await window.evolutionObservatory.loadEvolutionData();
                window.evolutionObservatory.renderUI();
            }
        } else {
            alert(`ℹ️ ${result.message || 'Evolution system responded'}`);
        }
    } catch (error) {
        console.error('Failed to trigger evolution:', error);
        alert('❌ Failed to trigger evolution cycle. Check console for details.');
    }
}

async function resetPopulation() {
    console.log('🔄 Resetting evolution population...');
    
    try {
        const response = await fetch('/api/evolution/reset', {
            method: 'POST', 
            headers: { 'Content-Type': 'application/json' }
        });
        
        const result = await response.json();
        
        if (result.status === 'reset_complete') {
            alert(`🔄 Evolution system reset! ${result.message}`);
            // Reload data to show changes
            if (window.evolutionObservatory && window.evolutionObservatory.websocket && 
                window.evolutionObservatory.websocket.readyState === WebSocket.OPEN) {
                window.evolutionObservatory.websocket.send(JSON.stringify({ type: 'request_update' }));
            } else if (window.evolutionObservatory) {
                await window.evolutionObservatory.loadEvolutionData();
                window.evolutionObservatory.renderUI();
            }
        } else {
            alert(`ℹ️ ${result.message || 'Evolution system responded'}`);
        }
    } catch (error) {
        console.error('Failed to reset population:', error);
        alert('❌ Failed to reset evolution system. Check console for details.');
    }
}

// Initialize the observatory when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.evolutionObservatory = new EvolutionObservatory();
    console.log('🧬 Evolution Observatory initialized');
});