"""
Emergent Evolution Engine v3.0 - Strategy Breeding and Emergent Intelligence

This module implements the next evolutionary step: strategies that breed and evolve
autonomously, creating novel optimization approaches through genetic algorithms.
"""
import asyncio
import random
import hashlib
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict

import structlog
from mcp_server.optimization_engine import OptimizationStrategy, optimization_engine

logger = structlog.get_logger(__name__)


@dataclass
class StrategyGene:
    """Genetic component of an optimization strategy."""
    trait_name: str
    trait_value: Any
    effectiveness: float = 0.5  # 0-1 effectiveness score
    stability: float = 0.5     # 0-1 stability score
    

@dataclass
class EvolutionaryStrategy:
    """Strategy with genetic information for breeding."""
    base_strategy: OptimizationStrategy
    genes: Dict[str, StrategyGene]
    generation: int = 0
    lineage: List[str] = field(default_factory=list)  # Parent strategy IDs
    fitness_score: float = 0.0
    

class EmergentEvolutionEngine:
    """
    v3.0 Emergent Evolution Engine
    
    Implements genetic algorithms for optimization strategy evolution:
    - Strategy breeding (combining successful strategies)
    - Mutation (random variations of successful approaches)
    - Natural selection (unsuccessful strategies die out)
    - Speciation (specialized strategies for different problem types)
    """
    
    def __init__(self):
        self.strategy_population: Dict[str, EvolutionaryStrategy] = {}
        self.extinct_strategies: Dict[str, EvolutionaryStrategy] = {}
        self.species: Dict[str, List[str]] = defaultdict(list)  # Species -> Strategy IDs
        self.generation_count = 0
        
        # Evolution parameters
        self.mutation_rate = 0.1
        self.crossover_rate = 0.7
        self.extinction_threshold = 0.2  # Fitness below this causes extinction
        self.population_limit = 20
        
    def initialize_population(self):
        """Initialize population with existing optimization strategies."""
        logger.info("Initializing evolutionary strategy population")
        
        # Convert existing strategies to evolutionary strategies
        for strategy_id, strategy in optimization_engine.strategies.items():
            genes = self._extract_genes_from_strategy(strategy)
            
            evolutionary_strategy = EvolutionaryStrategy(
                base_strategy=strategy,
                genes=genes,
                generation=0,
                lineage=[],
                fitness_score=0.5  # Neutral starting fitness
            )
            
            self.strategy_population[strategy_id] = evolutionary_strategy
            
            # Categorize into species based on strategy type
            species = self._classify_species(strategy)
            self.species[species].append(strategy_id)
        
        logger.info(f"Population initialized", 
                   population_size=len(self.strategy_population),
                   species_count=len(self.species))
    
    def _extract_genes_from_strategy(self, strategy: OptimizationStrategy) -> Dict[str, StrategyGene]:
        """Extract genetic traits from a strategy."""
        genes = {}
        
        # Extract complexity gene
        genes["complexity"] = StrategyGene(
            trait_name="complexity",
            trait_value=strategy.implementation_complexity,
            effectiveness=1.0 - (strategy.implementation_complexity / 10),  # Lower complexity = higher effectiveness
            stability=1.0 - (strategy.risk_level / 10)  # Lower risk = higher stability
        )
        
        # Extract risk tolerance gene
        genes["risk_tolerance"] = StrategyGene(
            trait_name="risk_tolerance", 
            trait_value=strategy.risk_level,
            effectiveness=strategy.expected_impact,
            stability=1.0 - (strategy.risk_level / 10)
        )
        
        # Extract parallel compatibility gene
        genes["parallel_ability"] = StrategyGene(
            trait_name="parallel_ability",
            trait_value=strategy.parallel_compatible,
            effectiveness=0.8 if strategy.parallel_compatible else 0.4,
            stability=0.7 if strategy.parallel_compatible else 0.8
        )
        
        # Extract domain gene based on description keywords
        domain = self._extract_domain_from_description(strategy.description)
        genes["domain"] = StrategyGene(
            trait_name="domain",
            trait_value=domain,
            effectiveness=0.6,  # Domain-specific effectiveness varies
            stability=0.7
        )
        
        return genes
    
    def _extract_domain_from_description(self, description: str) -> str:
        """Classify strategy domain based on description."""
        desc_lower = description.lower()
        
        if any(word in desc_lower for word in ["connection", "pool", "database"]):
            return "connection_management"
        elif any(word in desc_lower for word in ["parallel", "concurrent", "async"]):
            return "parallelization"
        elif any(word in desc_lower for word in ["cache", "caching", "memory"]):
            return "caching"
        elif any(word in desc_lower for word in ["load", "balance", "distribution"]):
            return "load_management"
        else:
            return "general_optimization"
    
    def _classify_species(self, strategy: OptimizationStrategy) -> str:
        """Classify strategy into evolutionary species."""
        if strategy.implementation_complexity >= 8:
            return "complex_optimizers"
        elif strategy.risk_level >= 7:
            return "high_risk_innovators"
        elif strategy.parallel_compatible:
            return "parallel_specialists"
        else:
            return "conservative_optimizers"
    
    async def evolve_generation(self) -> Dict[str, Any]:
        """Evolve the current generation of strategies."""
        logger.info(f"Starting generation {self.generation_count + 1} evolution")
        
        # Step 1: Fitness evaluation based on recent performance
        await self._evaluate_fitness()
        
        # Step 2: Natural selection - remove low-fitness strategies
        extinctions = self._natural_selection()
        
        # Step 3: Breeding - create new strategies from successful ones
        new_strategies = await self._breed_strategies()
        
        # Step 4: Mutation - random variations
        mutations = await self._mutate_strategies()
        
        # Step 5: Update population
        self.generation_count += 1
        
        evolution_summary = {
            "generation": self.generation_count,
            "population_size": len(self.strategy_population),
            "extinctions": extinctions,
            "new_strategies": len(new_strategies),
            "mutations": mutations,
            "species_count": len(self.species),
            "avg_fitness": self._calculate_average_fitness()
        }
        
        logger.info("Generation evolution complete", **evolution_summary)
        return evolution_summary
    
    async def _evaluate_fitness(self):
        """Evaluate fitness of each strategy based on performance history."""
        for strategy_id, evolutionary_strategy in self.strategy_population.items():
            
            # Get performance data from optimization engine
            pattern_key = f"strategy_type_{strategy_id}"
            success_rate = optimization_engine.optimization_patterns.get(pattern_key, 0.5)
            
            # Calculate fitness based on multiple factors
            effectiveness = success_rate
            efficiency = 1.0 - (evolutionary_strategy.base_strategy.implementation_complexity / 10)
            stability = 1.0 - (evolutionary_strategy.base_strategy.risk_level / 10)
            
            # Weighted fitness calculation
            fitness = (
                effectiveness * 0.5 +  # Success rate is most important
                efficiency * 0.3 +     # Lower complexity is better
                stability * 0.2        # Lower risk is better
            )
            
            evolutionary_strategy.fitness_score = fitness
            
            logger.debug(f"Strategy fitness evaluated",
                        strategy_id=strategy_id,
                        fitness=fitness,
                        success_rate=success_rate)
    
    def _natural_selection(self) -> List[str]:
        """Remove low-fitness strategies from population."""
        extinctions = []
        
        for strategy_id, evolutionary_strategy in list(self.strategy_population.items()):
            if evolutionary_strategy.fitness_score < self.extinction_threshold:
                # Strategy goes extinct
                self.extinct_strategies[strategy_id] = evolutionary_strategy
                del self.strategy_population[strategy_id]
                extinctions.append(strategy_id)
                
                # Remove from species
                for species, members in self.species.items():
                    if strategy_id in members:
                        members.remove(strategy_id)
                        break
                        
                logger.info(f"Strategy extinct due to low fitness",
                           strategy_id=strategy_id,
                           fitness=evolutionary_strategy.fitness_score)
        
        return extinctions
    
    async def _breed_strategies(self) -> List[str]:
        """Breed new strategies from successful parents."""
        new_strategies = []
        
        # Find high-fitness strategies for breeding
        breeding_candidates = [
            (sid, es) for sid, es in self.strategy_population.items()
            if es.fitness_score > 0.7
        ]
        
        if len(breeding_candidates) < 2:
            logger.info("Insufficient breeding candidates")
            return new_strategies
        
        # Generate offspring through crossover
        for i in range(min(3, len(breeding_candidates) // 2)):  # Max 3 new strategies per generation
            parent1_id, parent1 = random.choice(breeding_candidates)
            parent2_id, parent2 = random.choice(breeding_candidates)
            
            if parent1_id != parent2_id:  # No self-breeding
                offspring = await self._crossover_strategies(parent1, parent2)
                if offspring:
                    offspring_id = self._generate_strategy_id(parent1_id, parent2_id)
                    self.strategy_population[offspring_id] = offspring
                    new_strategies.append(offspring_id)
                    
                    # Classify into species
                    species = self._classify_species(offspring.base_strategy)
                    self.species[species].append(offspring_id)
                    
                    logger.info(f"New strategy bred",
                               offspring_id=offspring_id,
                               parent1=parent1_id,
                               parent2=parent2_id)
        
        return new_strategies
    
    async def _crossover_strategies(self, parent1: EvolutionaryStrategy, parent2: EvolutionaryStrategy) -> Optional[EvolutionaryStrategy]:
        """Create offspring strategy by combining traits from two parents."""
        
        # Combine genes from both parents
        offspring_genes = {}
        
        for gene_name in set(parent1.genes.keys()) | set(parent2.genes.keys()):
            if gene_name in parent1.genes and gene_name in parent2.genes:
                # Both parents have this gene - choose the more effective one
                gene1 = parent1.genes[gene_name]
                gene2 = parent2.genes[gene_name]
                
                if gene1.effectiveness > gene2.effectiveness:
                    offspring_genes[gene_name] = gene1
                else:
                    offspring_genes[gene_name] = gene2
            
            elif gene_name in parent1.genes:
                offspring_genes[gene_name] = parent1.genes[gene_name]
            else:
                offspring_genes[gene_name] = parent2.genes[gene_name]
        
        # Create hybrid strategy
        offspring_strategy = OptimizationStrategy(
            id="",  # Will be set by caller
            description=f"Hybrid of {parent1.base_strategy.description[:30]}... and {parent2.base_strategy.description[:30]}...",
            implementation_complexity=int((parent1.base_strategy.implementation_complexity + parent2.base_strategy.implementation_complexity) / 2),
            risk_level=int((parent1.base_strategy.risk_level + parent2.base_strategy.risk_level) / 2),
            expected_impact=(parent1.base_strategy.expected_impact + parent2.base_strategy.expected_impact) / 2,
            rollback_strategy="Combined rollback approach from parent strategies",
            success_criteria=list(set(parent1.base_strategy.success_criteria + parent2.base_strategy.success_criteria)),
            parallel_compatible=parent1.base_strategy.parallel_compatible and parent2.base_strategy.parallel_compatible
        )
        
        offspring = EvolutionaryStrategy(
            base_strategy=offspring_strategy,
            genes=offspring_genes,
            generation=self.generation_count + 1,
            lineage=[parent1.base_strategy.id, parent2.base_strategy.id],
            fitness_score=0.5  # Neutral starting fitness
        )
        
        return offspring
    
    async def _mutate_strategies(self) -> int:
        """Apply random mutations to strategies."""
        mutations = 0
        
        for strategy_id, evolutionary_strategy in self.strategy_population.items():
            if random.random() < self.mutation_rate:
                # Apply random mutation
                mutation_applied = self._apply_random_mutation(evolutionary_strategy)
                if mutation_applied:
                    mutations += 1
                    logger.info(f"Strategy mutated", strategy_id=strategy_id)
        
        return mutations
    
    def _apply_random_mutation(self, strategy: EvolutionaryStrategy) -> bool:
        """Apply a random mutation to a strategy."""
        mutation_types = ["complexity", "risk", "parallel", "domain"]
        mutation_type = random.choice(mutation_types)
        
        if mutation_type == "complexity":
            # Mutate complexity by ±1
            delta = random.choice([-1, 1])
            new_complexity = max(1, min(10, strategy.base_strategy.implementation_complexity + delta))
            strategy.base_strategy.implementation_complexity = new_complexity
            strategy.genes["complexity"].trait_value = new_complexity
            return True
        
        elif mutation_type == "risk":
            # Mutate risk level by ±1
            delta = random.choice([-1, 1])  
            new_risk = max(1, min(10, strategy.base_strategy.risk_level + delta))
            strategy.base_strategy.risk_level = new_risk
            strategy.genes["risk_tolerance"].trait_value = new_risk
            return True
        
        elif mutation_type == "parallel":
            # Flip parallel compatibility
            strategy.base_strategy.parallel_compatible = not strategy.base_strategy.parallel_compatible
            strategy.genes["parallel_ability"].trait_value = strategy.base_strategy.parallel_compatible
            return True
        
        return False
    
    def _generate_strategy_id(self, parent1_id: str, parent2_id: str) -> str:
        """Generate unique ID for offspring strategy."""
        lineage_str = f"{parent1_id}+{parent2_id}+gen{self.generation_count}"
        hash_obj = hashlib.md5(lineage_str.encode())
        return f"evolved_{hash_obj.hexdigest()[:8]}"
    
    def _calculate_average_fitness(self) -> float:
        """Calculate average fitness of current population."""
        if not self.strategy_population:
            return 0.0
        
        total_fitness = sum(es.fitness_score for es in self.strategy_population.values())
        return total_fitness / len(self.strategy_population)
    
    async def run_evolutionary_cycle(self, generations: int = 3) -> Dict[str, Any]:
        """Run multiple generations of evolution."""
        logger.info(f"Starting {generations}-generation evolutionary cycle")
        
        if not self.strategy_population:
            self.initialize_population()
        
        evolution_history = []
        
        for gen in range(generations):
            generation_result = await self.evolve_generation()
            evolution_history.append(generation_result)
            
            # Brief pause between generations
            await asyncio.sleep(0.1)
        
        summary = {
            "total_generations": generations,
            "final_population_size": len(self.strategy_population),
            "total_extinctions": len(self.extinct_strategies),
            "species_diversity": len([s for s in self.species.values() if s]),
            "final_average_fitness": self._calculate_average_fitness(),
            "evolution_history": evolution_history
        }
        
        logger.info("Evolutionary cycle complete", **summary)
        return summary
    
    def get_evolutionary_insights(self) -> Dict[str, Any]:
        """Get insights into evolutionary patterns and emergent behaviors."""
        
        # Analyze successful lineages
        successful_lineages = []
        for strategy_id, strategy in self.strategy_population.items():
            if strategy.fitness_score > 0.8 and strategy.lineage:
                successful_lineages.append({
                    "id": strategy_id,
                    "parents": strategy.lineage,
                    "generation": strategy.generation,
                    "fitness": strategy.fitness_score
                })
        
        # Analyze species evolution
        species_stats = {}
        for species_name, members in self.species.items():
            if members:
                fitnesses = [self.strategy_population[mid].fitness_score for mid in members if mid in self.strategy_population]
                species_stats[species_name] = {
                    "population": len(members),
                    "avg_fitness": sum(fitnesses) / len(fitnesses) if fitnesses else 0,
                    "max_fitness": max(fitnesses) if fitnesses else 0
                }
        
        return {
            "population_size": len(self.strategy_population),
            "extinct_species": len(self.extinct_strategies),
            "generation_count": self.generation_count,
            "successful_lineages": successful_lineages,
            "species_evolution": species_stats,
            "emergent_behaviors": self._detect_emergent_behaviors()
        }
    
    def _detect_emergent_behaviors(self) -> List[str]:
        """Detect emergent evolutionary behaviors."""
        behaviors = []
        
        # Check for convergent evolution
        high_fitness_strategies = [s for s in self.strategy_population.values() if s.fitness_score > 0.8]
        if len(high_fitness_strategies) > 1:
            # Look for similar traits
            common_traits = set(high_fitness_strategies[0].genes.keys())
            for strategy in high_fitness_strategies[1:]:
                common_traits &= set(strategy.genes.keys())
            
            if len(common_traits) >= 3:
                behaviors.append("Convergent evolution toward optimal trait combinations")
        
        # Check for speciation
        if len([s for s in self.species.values() if s]) > 3:
            behaviors.append("Speciation into distinct optimization niches")
        
        # Check for hybrid vigor
        hybrid_strategies = [s for s in self.strategy_population.values() if len(s.lineage) >= 2]
        if hybrid_strategies:
            avg_hybrid_fitness = sum(s.fitness_score for s in hybrid_strategies) / len(hybrid_strategies)
            if avg_hybrid_fitness > 0.7:
                behaviors.append("Hybrid vigor - offspring outperforming parents")
        
        return behaviors


# Global emergent evolution engine
emergent_engine = EmergentEvolutionEngine()