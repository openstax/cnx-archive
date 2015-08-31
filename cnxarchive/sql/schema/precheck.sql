DO LANGUAGE plpgsql
$$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_class WHERE relname='modules') THEN
    RAISE EXCEPTION USING MESSAGE = 'Database is already initialized.';
  END IF;
END;
$$;
