# Stage 1: Build the JAR
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /app
COPY pom.xml ./
# Download dependencies first (Caching layer)
RUN mvn dependency:go-offline
COPY src ./src
RUN mvn clean package -DskipTests

# Stage 2: Run the App
FROM eclipse-temurin:17-jre-jammy
WORKDIR /app
COPY --from=build /app/target/*.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]