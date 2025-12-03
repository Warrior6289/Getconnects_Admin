with open('.env', 'w') as f:
    f.write("DATABASE_URL='postgresql://postgres.eirzrqlkjxvxahoulybz:prNnTjYA8$vbPua@aws-0-ap-south-1.pooler.supabase.com:5432/postgres'\n")
    f.write("FLASK_SECRET_KEY='dev_secret_key_change_in_production_12345'\n")
    f.write("ENCRYPTION_KEY='dev_encryption_key_change_in_production_67890'\n")
