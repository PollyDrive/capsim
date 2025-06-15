import psycopg2
from psycopg2.extras import execute_values
from faker import Faker
from capsim.utils.db_connector import get_db_connection
from capsim.models.base import Person, Gender, Cluster, Profession
import random

PROFESSION_DATA = {
    Profession.SHOP_CLERK: {"cluster": Cluster.WORKER, "count": 180, "attrs": {"financial_capability": (1, 3), "trend_receptivity": (2, 4), "social_status": (1, 2), "energy_level": (2, 5), "time_budget": (1, 3)}},
    Profession.ARTISAN: {"cluster": Cluster.WORKER, "count": 70, "attrs": {"financial_capability": (2, 4), "trend_receptivity": (3, 5), "social_status": (1, 2), "energy_level": (2, 5), "time_budget": (2, 4)}},
    Profession.DEVELOPER: {"cluster": Cluster.WORKER, "count": 120, "attrs": {"financial_capability": (3, 5), "trend_receptivity": (2, 4), "social_status": (2, 4), "energy_level": (2, 5), "time_budget": (2, 4)}},
    Profession.POLITICIAN: {"cluster": Cluster.SOCIAL, "count": 10, "attrs": {"financial_capability": (4, 5), "trend_receptivity": (2, 4), "social_status": (4, 5), "energy_level": (2, 4), "time_budget": (1, 3)}},
    Profession.BLOGGER: {"cluster": Cluster.SOCIAL, "count": 50, "attrs": {"financial_capability": (2, 4), "trend_receptivity": (4, 5), "social_status": (3, 5), "energy_level": (2, 5), "time_budget": (3, 4)}},
    Profession.MARKETER: {"cluster": Cluster.SOCIAL, "count": 60, "attrs": {"financial_capability": (3, 4), "trend_receptivity": (3, 5), "social_status": (3, 4), "energy_level": (2, 5), "time_budget": (2, 4)}},
    Profession.BUSINESSMAN: {"cluster": Cluster.SOCIAL, "count": 80, "attrs": {"financial_capability": (4, 5), "trend_receptivity": (2, 4), "social_status": (3, 5), "energy_level": (2, 5), "time_budget": (1, 3)}},
    Profession.SPIRITUAL_MENTOR: {"cluster": Cluster.SPIRITUAL, "count": 30, "attrs": {"financial_capability": (1, 3), "trend_receptivity": (2, 5), "social_status": (2, 5), "energy_level": (3, 5), "time_budget": (2, 4)}},
    Profession.PHILOSOPHER: {"cluster": Cluster.SPIRITUAL, "count": 20, "attrs": {"financial_capability": (1, 3), "trend_receptivity": (1, 3), "social_status": (1, 4), "energy_level": (2, 4), "time_budget": (2, 4)}},
    Profession.STUDENT: {"cluster": Cluster.OTHER, "count": 200, "attrs": {"financial_capability": (1, 2), "trend_receptivity": (2, 4), "social_status": (1, 2), "energy_level": (3, 5), "time_budget": (1, 4)}},
    Profession.UNEMPLOYED: {"cluster": Cluster.OTHER, "count": 90, "attrs": {"financial_capability": (1, 2), "trend_receptivity": (1, 3), "social_status": (1, 2), "energy_level": (1, 3), "time_budget": (3, 5)}},
    Profession.ATHLETE: {"cluster": Cluster.OTHER, "count": 80, "attrs": {"financial_capability": (2, 4), "trend_receptivity": (1, 3), "social_status": (1, 4), "energy_level": (4, 5), "time_budget": (2, 4)}},
    Profession.FRAUDSTER: {"cluster": Cluster.OTHER, "count": 10, "attrs": {"financial_capability": (2, 5), "trend_receptivity": (1, 3), "social_status": (1, 4), "energy_level": (2, 4), "time_budget": (3, 5)}},
}

def get_age_for_profession(profession: Profession) -> int:
    if profession == Profession.STUDENT:
        return random.randint(18, 24)
    if profession == Profession.POLITICIAN:
        return random.randint(35, 70)
    return random.randint(25, 65)

def generate_persons(num_persons: int) -> list[tuple]:
    """
    Generates a list of person data tuples for database insertion.
    """
    fake = Faker()
    persons_data = []

    profession_pool = [prof for prof, data in PROFESSION_DATA.items() for _ in range(data["count"])]
    
    if num_persons > len(profession_pool):
        print(f"Warning: Requested {num_persons} but only {len(profession_pool)} are defined. Generating {len(profession_pool)}.")
        num_persons = len(profession_pool)
        
    random.shuffle(profession_pool)

    for i in range(num_persons):
        profession = profession_pool[i]
        prof_data = PROFESSION_DATA[profession]
        
        person_attrs = {key: round(random.uniform(val[0], val[1]), 2) for key, val in prof_data["attrs"].items()}

        person = Person(
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            age=get_age_for_profession(profession),
            gender=random.choice(list(Gender)),
            cluster=prof_data["cluster"],
            profession=profession,
            **person_attrs
        )
        persons_data.append((
            person.id, person.first_name, person.last_name, person.middle_name, person.age,
            person.gender.value, person.cluster.value, person.profession.value,
            person.financial_capability, person.trend_receptivity, person.social_status,
            person.energy_level, person.time_budget, person.created_at
        ))
    return persons_data

def seed_database(num_persons: int = 1000):
    """
    Seeds the database with an initial population of persons if it's empty.
    """
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            print("Failed to get database connection.")
            return

        cur = conn.cursor()

        cur.execute("SELECT 1 FROM persons LIMIT 1;")
        if cur.fetchone():
            print("Database already seeded. Exiting.")
            return

        persons_to_insert = generate_persons(num_persons)
        
        insert_query = """
            INSERT INTO persons (
                id, first_name, last_name, middle_name, age, gender, cluster,
                profession, financial_capability, trend_receptivity, social_status,
                energy_level, time_budget, created_at
            )
            VALUES %s;
        """
        
        execute_values(cur, insert_query, persons_to_insert)
        
        conn.commit()
        print(f"Successfully seeded database with {cur.rowcount} persons.")
        cur.close()

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Error seeding database: {error}")
    finally:
        if conn is not None:
            conn.close()

if __name__ == '__main__':
    seed_database() 