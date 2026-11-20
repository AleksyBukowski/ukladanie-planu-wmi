import csv
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

# Ustawienie stałego ziarna losowości dla powtarzalności wyników
random.seed(42)


# --- 1. GENEROWANIE SAL (30 sal) ---
def generate_rooms():
    rooms = []
    # 6 sal wykładowych
    for i in range(1, 7):
        rooms.append({"code": f"A0.{i:02d}", "capacity": 120, "room_type": "lecture_hall"})
    # 12 sal ćwiczeniowych
    for i in range(1, 13):
        rooms.append({"code": f"A1.{i:02d}", "capacity": 32, "room_type": "classroom"})
    # 12 pracowni komputerowych/labów
    for i in range(1, 13):
        rooms.append({"code": f"L2.{i:02d}", "capacity": 30, "room_type": "lab"})

    with open(BASE_DIR / "rooms.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["code", "capacity", "room_type"])
        writer.writeheader()
        writer.writerows(rooms)
    return rooms


# --- 2. GENEROWANIE PROWADZĄCYCH (100 prowadzących) ---
def generate_teachers():
    first_names = [
        "Jan",
        "Piotr",
        "Tomasz",
        "Michał",
        "Krzysztof",
        "Andrzej",
        "Anna",
        "Maria",
        "Katarzyna",
        "Agnieszka",
        "Ewa",
        "Magdalena",
    ]
    last_names = [
        "Nowak",
        "Kowalski",
        "Wiśniewski",
        "Wójcik",
        "Kowalczyk",
        "Kamiński",
        "Lewandowski",
        "Zieliński",
        "Szymański",
        "Woźniak",
        "Dąbrowski",
        "Kozłowski",
    ]
    titles = ["mgr", "dr", "dr hab.", "prof."]

    teachers = []
    for i in range(1, 101):
        teachers.append(
            {
                "external_id": f"T{i:03d}",
                "title": random.choices(titles, weights=[0.2, 0.5, 0.2, 0.1])[0],
                "first_name": random.choice(first_names),
                "last_name": f"{random.choice(last_names)}_{i}",  # syntetyczny sufiks
            }
        )

    with open(BASE_DIR / "teachers.csv", "w", newline="", encoding="utf-8") as f:
        fieldnames = ["external_id", "title", "first_name", "last_name"]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(teachers)
    return teachers


# --- 3. GENEROWANIE PRZEDMIOTÓW (40 przedmiotów) ---
def generate_courses():
    courses_data = [
        ("WDI", "Wstęp do informatyki"),
        ("ASD", "Algorytmy i struktury danych"),
        ("BD", "Bazy danych"),
        ("SO", "Systemy operacyjne"),
        ("SK", "Sieci komputerowe"),
        ("PO", "Programowanie obiektowe"),
        ("IO", "Inżynieria oprogramowania"),
        ("AM1", "Analiza matematyczna 1"),
        ("AM2", "Analiza matematyczna 2"),
        ("GAL", "Geometria z algebrą liniową"),
        ("MD", "Matematyka dyskretna"),
        ("RP", "Rachunek prawdopodobieństwa"),
        ("MN", "Metody numeryczne"),
        ("WWW", "Technologie webowe"),
        ("AOD", "Algorytmy optymalizacji dyskretnej"),
        ("KRYP", "Kryptografia i bezpieczeństwo"),
        ("SZT", "Sztuczna inteligencja"),
        ("ML", "Uczenie maszynowe"),
        ("ANG1", "Język angielski B2"),
        ("ANG2", "Język angielski C1"),
    ]
    # Dodajemy warianty zaawansowane, aby łącznie było 40 przedmiotów
    all_courses = []
    for code, name in courses_data:
        all_courses.append({"code": code, "name": name})
        all_courses.append(
            {"code": f"{code}-ADV", "name": f"{name} (zaawansowane)"}
        )

    with open(BASE_DIR / "courses.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["code", "name"])
        writer.writeheader()
        writer.writerows(all_courses)
    return all_courses


# --- 4. GENEROWANIE GRUP (50 grup) ---
def generate_groups():
    groups = []
    majors = ["INF", "MATH", "BIOINF", "DATA"]
    group_counter = 1

    for major in majors:
        for year in [1, 2, 3]:
            for grp_letter in ["A", "B", "C", "D"]:
                if group_counter > 50:
                    break
                code = f"{major}-{year}{grp_letter}"
                name = f"Kierunek {major}, rok {year}, grupa {grp_letter}"
                size = random.randint(22, 30)
                groups.append({"code": code, "name": name, "size": size})
                group_counter += 1
            if group_counter > 50:
                break
        if group_counter > 50:
            break

    with open(BASE_DIR / "groups.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["code", "name", "size"])
        writer.writeheader()
        writer.writerows(groups)
    return groups


# --- 5. GENEROWANIE PRZYDZIAŁÓW ZAJĘĆ (600 zajęć) ---
def generate_assignments(courses, teachers, groups):
    assignments = []
    class_types = [
        ("lab", "lab"),
        ("exercises", "classroom"),
        ("lecture", "lecture_hall"),
    ]

    for _ in range(600):
        course = random.choice(courses)
        teacher = random.choice(teachers)
        group = random.choice(groups)
        c_type, r_type = random.choice(class_types)

        assignments.append(
            {
                "course_code": course["code"],
                "teacher_external_id": teacher["external_id"],
                "group_code": group["code"],
                "class_type": c_type,
                "required_room_type": r_type,
                "units_per_week": 1,
            }
        )

    fieldnames = [
        "course_code",
        "teacher_external_id",
        "group_code",
        "class_type",
        "required_room_type",
        "units_per_week",
    ]
    with open(
        BASE_DIR / "assignments.csv", "w", newline="", encoding="utf-8"
    ) as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(assignments)
    return assignments


if __name__ == "__main__":
    print("Generowanie syntetycznego zbioru danych referencyjnych...")
    rooms = generate_rooms()
    teachers = generate_teachers()
    courses = generate_courses()
    groups = generate_groups()
    assignments = generate_assignments(courses, teachers, groups)
    print("Sukces!")
    print(f"- Sale (rooms.csv): {len(rooms)}")
    print(f"- Prowadzący (teachers.csv): {len(teachers)}")
    print(f"- Przedmioty (courses.csv): {len(courses)}")
    print(f"- Grupy (groups.csv): {len(groups)}")
    print(f"- Przydziały (assignments.csv): {len(assignments)}")
