from setuptools import setup, find_packages

setup(
    name="chat-platform",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "fastapi>=0.110.2",
        "uvicorn>=0.29.0",
        "sqlalchemy>=2.0.29",
        "pydantic>=2.7.1",
        "pydantic-settings>=2.2.1",
        "python-jose[cryptography]>=3.3.0",
        "passlib[bcrypt]>=1.7.4",
        "python-multipart>=0.0.9",
        "alembic>=1.13.1",
        "python-dotenv>=1.0.1",
        "structlog>=24.1.0",
    ],
) 