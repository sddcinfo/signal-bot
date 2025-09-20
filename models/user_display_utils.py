"""
Centralized user display utilities for consistent name display across the application.
"""

def get_user_display_sql(table_alias: str = "u") -> str:
    """
    Get the SQL snippet for consistent user display name calculation.

    Priority order (excluding username):
    1. contact_name (address book name like "Brad Smith")
    2. given_name + family_name (like "Brad Smith")
    3. given_name only
    4. family_name only
    5. profile_given_name + profile_family_name
    6. profile_given_name only
    7. profile_family_name only
    8. friendly_name (fallback for existing data)
    9. phone_number
    10. UUID (absolute last resort)

    Args:
        table_alias: The table alias for the users table (default: "u")

    Returns:
        SQL snippet for COALESCE user display logic
    """
    return f"""COALESCE(
        NULLIF(TRIM({table_alias}.contact_name), ''),
        CASE
            WHEN NULLIF(TRIM({table_alias}.given_name), '') IS NOT NULL AND NULLIF(TRIM({table_alias}.family_name), '') IS NOT NULL
            THEN TRIM({table_alias}.given_name) || ' ' || TRIM({table_alias}.family_name)
            WHEN NULLIF(TRIM({table_alias}.given_name), '') IS NOT NULL
            THEN TRIM({table_alias}.given_name)
            WHEN NULLIF(TRIM({table_alias}.family_name), '') IS NOT NULL
            THEN TRIM({table_alias}.family_name)
            ELSE NULL
        END,
        CASE
            WHEN NULLIF(TRIM({table_alias}.profile_given_name), '') IS NOT NULL AND NULLIF(TRIM({table_alias}.profile_family_name), '') IS NOT NULL
            THEN TRIM({table_alias}.profile_given_name) || ' ' || TRIM({table_alias}.profile_family_name)
            WHEN NULLIF(TRIM({table_alias}.profile_given_name), '') IS NOT NULL
            THEN TRIM({table_alias}.profile_given_name)
            WHEN NULLIF(TRIM({table_alias}.profile_family_name), '') IS NOT NULL
            THEN TRIM({table_alias}.profile_family_name)
            ELSE NULL
        END,
        NULLIF(TRIM({table_alias}.friendly_name), ''),
        {table_alias}.phone_number,
        {table_alias}.uuid
    )"""