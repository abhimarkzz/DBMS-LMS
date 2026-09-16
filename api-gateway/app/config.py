from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    USER_SERVICE_URL: str = "http://user-service:8001"
    COURSE_SERVICE_URL: str = "http://course-service:8002"
    RESULT_SERVICE_URL: str = "http://result-service:8003"
    NOTIFICATION_SERVICE_URL: str = "http://notification-service:8004"
    ASSIGNMENT_SERVICE_URL: str = "http://assignment-service:8005"
    
    class Config:
        env_file = ".env"

settings = Settings()
