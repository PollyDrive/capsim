import logging
import json
import psycopg2
from psycopg2.extras import Json
from typing import List, Dict, Optional
from uuid import UUID
from ..models.base import Person, SimulationConfig
from ..actions.base import Action
from ..utils.db_connector import get_db_connection

logger = logging.getLogger(__name__)

class SimulationEngine:
    def __init__(self, config: SimulationConfig):
        self.config = config
        self.people: List[Person] = []
        self.available_actions: List[Action] = []
        self.current_tick: int = 0
        self._setup_logging()
    
    def _setup_logging(self):
        """Configure logging for the simulation"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    def _load_people_from_db(self):
        """Load the initial population from the database."""
        conn = None
        try:
            conn = get_db_connection()
            if conn is None:
                logger.error("Could not establish database connection.")
                return
            
            cur = conn.cursor()
            cur.execute("""
                SELECT id, first_name, last_name, middle_name, age, gender, cluster,
                    profession, financial_capability, trend_receptivity, social_status,
                    energy_level, time_budget, created_at
                FROM persons;
            """)
            person_records = cur.fetchall()
            
            self.people = [Person(
                id=rec[0],
                first_name=rec[1],
                last_name=rec[2],
                middle_name=rec[3],
                age=rec[4],
                gender=rec[5],
                cluster=rec[6],
                profession=rec[7],
                financial_capability=rec[8],
                trend_receptivity=rec[9],
                social_status=rec[10],
                energy_level=rec[11],
                time_budget=rec[12],
                created_at=rec[13]
            ) for rec in person_records]
            
            logger.info(f"Loaded {len(self.people)} people from the database.")
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(f"Error loading people from DB: {error}")
        finally:
            if conn is not None:
                conn.close()

    def add_person(self, person: Person) -> None:
        """Add a person to the simulation"""
        self.people.append(person)
        logger.info(f"Added person {person.id} to simulation")
    
    def add_action(self, action: Action) -> None:
        """Add an available action to the simulation"""
        self.available_actions.append(action)
        logger.debug(f"Added action {action.name} to available actions")
    
    def _log_event(self, person_id: UUID, event_type: str, details: Dict):
        """Log a single event to the database."""
        conn = None
        try:
            conn = get_db_connection()
            if conn is None:
                logger.error("Could not establish database connection for logging.")
                return

            cur = conn.cursor()
            insert_query = "INSERT INTO events (actor_id, event_type, details) VALUES (%s, %s, %s);"
            cur.execute(insert_query, (person_id, event_type, Json(details)))
            conn.commit()
            cur.close()
        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(f"Error logging event type {event_type}: {error}")
        finally:
            if conn is not None:
                conn.close()

    def _apply_global_factors(self) -> None:
        """Apply global factors to all people."""
        # Placeholder for future global factors like economic trends, etc.
        pass
    
    def _process_person_actions(self, person: Person) -> None:
        """Process available actions for a person"""
        available_actions = [
            action for action in self.available_actions 
            if action.can_execute(person)
        ]
        
        if available_actions:
            # Simple implementation - take first available action
            # TODO: Implement more sophisticated decision making
            action = available_actions[0]

            old_state = person.model_copy(deep=True)
            
            if action.execute(person):
                details = {
                    "action_name": action.name,
                    "cost": action.cost,
                    "state_before": old_state.model_dump(exclude={'actions_history'}),
                    "state_after": person.model_dump(exclude={'actions_history'})
                }
                self._log_event(person.id, event_type=action.name, details=details)
                logger.debug(f"Person {person.id} executed action {action.name}")
    
    def _update_people_in_db(self):
        """Update the state of all persons in the database."""
        conn = None
        try:
            conn = get_db_connection()
            if conn is None:
                logger.error("Could not establish database connection for updating people.")
                return

            cur = conn.cursor()
            
            # Crude age progression
            age_increase = self.config.simulation_days / 365.0
            
            update_data = [
                (p.id, p.age + age_increase, p.financial_capability, p.trend_receptivity,
                 p.social_status, p.energy_level, p.time_budget)
                for p in self.people
            ]

            from psycopg2.extras import execute_values
            execute_values(
                cur,
                """
                UPDATE persons SET
                    age = data.age,
                    financial_capability = data.financial_capability,
                    trend_receptivity = data.trend_receptivity,
                    social_status = data.social_status,
                    energy_level = data.energy_level,
                    time_budget = data.time_budget
                FROM (VALUES %s) AS data (id, age, financial_capability, trend_receptivity, social_status, energy_level, time_budget)
                WHERE persons.id = data.id;
                """,
                update_data,
                template='(%s, %s, %s, %s, %s, %s, %s)'
            )
            
            conn.commit()
            logger.info(f"Updated {len(self.people)} people in the database.")
            cur.close()

        except (Exception, psycopg2.DatabaseError) as error:
            logger.error(f"Error updating people in DB: {error}")
        finally:
            if conn is not None:
                conn.close()
    
    def tick(self) -> None:
        """Execute one tick of the simulation"""
        self.current_tick += 1
        logger.info(f"Starting tick {self.current_tick}")
        
        for person in self.people:
            self._process_person_actions(person)
        
        self._apply_global_factors()
        
        logger.info(f"Completed tick {self.current_tick}")
    
    def run(self) -> None:
        """Run the simulation for the configured number of days"""
        logger.info("Starting simulation")
        
        self._load_people_from_db()
        if not self.people:
            logger.error("No people loaded. Please seed the database first using 'scripts/seed_data.py'.")
            return

        for _ in range(self.config.simulation_days):
            self.tick()
        
        self._update_people_in_db()
        
        logger.info("Simulation completed") 