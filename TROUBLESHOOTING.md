# Troubleshooting Guide

## 🚀 Quick Fixes for Slow Startup

### 1. **Clean Docker Environment**
```bash
# Stop all containers
docker-compose down

# Remove all containers and volumes
docker-compose down -v

# Clean Docker cache
docker system prune -a

# Rebuild from scratch
docker-compose build --no-cache
docker-compose up -d
```

### 2. **Check Resource Usage**
```bash
# Check Docker resource usage
docker stats

# Check disk space
df -h

# Check memory usage
free -h
```

### 3. **Monitor Startup Process**
```bash
# Watch logs in real-time
docker-compose logs -f

# Check specific service logs
docker-compose logs -f web
docker-compose logs -f db
docker-compose logs -f redis
```

## 🔧 Common Issues and Solutions

### **Issue: Services taking too long to start**

**Symptoms:**
- `docker-compose up` hangs for 800+ seconds
- Health checks failing
- Services not responding

**Solutions:**
1. **Increase Docker resources:**
   - Open Docker Desktop → Settings → Resources
   - Increase Memory to 4GB+
   - Increase CPU to 2+

2. **Optimize health checks:**
   ```yaml
   healthcheck:
     test: ["CMD-SHELL", "pg_isready -U webcrawler -d webcrawler"]
     interval: 10s
     timeout: 5s
     retries: 5
     start_period: 30s
   ```

3. **Use lightweight requirements:**
   - Use `requirements-dev.txt` instead of full `requirements.txt`
   - Excludes heavy ML libraries (torch, transformers)

### **Issue: Database connection errors**

**Symptoms:**
- Django can't connect to PostgreSQL
- Migration errors
- Database timeout

**Solutions:**
1. **Wait for database to be ready:**
   ```bash
   # Check database status
   docker-compose exec db pg_isready -U webcrawler
   ```

2. **Run migrations manually:**
   ```bash
   docker-compose exec web python manage.py migrate
   ```

3. **Reset database:**
   ```bash
   docker-compose down -v
   docker-compose up -d db
   sleep 10
   docker-compose up -d
   ```

### **Issue: Redis connection errors**

**Symptoms:**
- Celery can't connect to Redis
- Redis connection timeout

**Solutions:**
1. **Check Redis status:**
   ```bash
   docker-compose exec redis redis-cli ping
   ```

2. **Restart Redis:**
   ```bash
   docker-compose restart redis
   ```

### **Issue: Port conflicts**

**Symptoms:**
- "Port already in use" errors
- Services can't bind to ports

**Solutions:**
1. **Check port usage:**
   ```bash
   # Check what's using port 8000
   lsof -i :8000
   
   # Check what's using port 5432
   lsof -i :5432
   ```

2. **Change ports in docker-compose.yml:**
   ```yaml
   ports:
     - "8001:8000"  # Change external port
   ```

## 🚀 Performance Optimization

### **1. Use Development Mode**
```bash
# Use lightweight requirements
cp requirements-dev.txt requirements.txt

# Rebuild with dev requirements
docker-compose build --no-cache
```

### **2. Optimize Docker Settings**
- **Memory:** 4GB minimum
- **CPU:** 2 cores minimum
- **Disk:** 20GB free space
- **Swap:** 2GB

### **3. Use Volume Caching**
```yaml
volumes:
  - .:/app
  - pip_cache:/root/.cache/pip  # Cache pip packages
```

### **4. Parallel Service Startup**
```yaml
depends_on:
  db:
    condition: service_healthy
  redis:
    condition: service_healthy
```

## 📊 Monitoring Commands

### **Check Service Health**
```bash
# All services
docker-compose ps

# Service logs
docker-compose logs web
docker-compose logs celery
docker-compose logs db
docker-compose logs redis

# Resource usage
docker stats
```

### **Test API Endpoints**
```bash
# Test health endpoint
curl http://localhost:8000/api/crawler/stats/

# Test database connection
docker-compose exec web python manage.py check --database default
```

### **Debug Specific Issues**
```bash
# Enter container shell
docker-compose exec web bash

# Check Django settings
docker-compose exec web python manage.py check

# Check database migrations
docker-compose exec web python manage.py showmigrations
```

## 🔄 Quick Restart Commands

### **Full Restart**
```bash
./start.sh
```

### **Service Restart**
```bash
# Restart specific service
docker-compose restart web

# Restart all services
docker-compose restart
```

### **Clean Restart**
```bash
docker-compose down -v
docker-compose up -d --build
```

## 📝 Expected Startup Times

- **PostgreSQL:** 10-30 seconds
- **Redis:** 5-10 seconds
- **Django Web:** 30-60 seconds (with migrations)
- **Celery Worker:** 10-20 seconds
- **Celery Beat:** 10-20 seconds

**Total expected time:** 1-2 minutes

If startup takes longer than 3 minutes, there's likely an issue to investigate.

## 🆘 Still Having Issues?

1. **Check logs:** `docker-compose logs -f`
2. **Verify resources:** Ensure Docker has enough memory/CPU
3. **Clean environment:** `docker system prune -a`
4. **Use development setup:** Use `requirements-dev.txt`
5. **Check network:** Ensure ports 8000, 5432, 6379 are free

For persistent issues, check the logs for specific error messages and consult the error handling section above.
