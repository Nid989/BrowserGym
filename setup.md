# WebArena Project Setup Documentation

## Prerequisites

- Access to AWS EC2 instance
- Python environment (3.10+)
- Docker installed locally
- OpenAI and LangChain API keys
- webarena-server-kp.pem file (will be provided separately)

## 1. EC2 Instance Connection 
```
# SSH into EC2 instance using provided .pem file
ssh -i webarena-server-kp.pem ubuntu@18.223.217.129
```

NOTE: The following 2 steps should be executed under the EC2 `webarena_server`.

## 2. Start WebArena Services
```
# Start Docker containers
docker start gitlab
docker start shopping
docker start shopping_admin
docker start forum
docker start kiwix33

# Start OpenStreetMap service
cd /home/ubuntu/openstreetmap-website/
docker compose start

# Wait ~1 minute for services to initialize
```

## 3. Configure Service URLs

# Configure Shopping Service
```
docker exec shopping /var/www/magento2/bin/magento setup:store-config:set --base-url="http://ec2-18-223-217-129.us-east-2.compute.amazonaws.com:7770"
docker exec shopping mysql -u magentouser -pMyPassword magentodb -e  'UPDATE core_config_data SET value="http://ec2-18-223-217-129.us-east-2.compute.amazonaws.com:7770/" WHERE path = "web/secure/base_url";'

# Configure Admin Settings
docker exec shopping_admin php /var/www/magento2/bin/magento config:set admin/security/password_is_forced 0
docker exec shopping_admin php /var/www/magento2/bin/magento config:set admin/security/password_lifetime 0
docker exec shopping /var/www/magento2/bin/magento cache:flush

# Configure Shopping Admin Service
docker exec shopping_admin /var/www/magento2/bin/magento setup:store-config:set --base-url="http://ec2-18-223-217-129.us-east-2.compute.amazonaws.com:7780"
docker exec shopping_admin mysql -u magentouser -pMyPassword magentodb -e  'UPDATE core_config_data SET value="http://ec2-18-223-217-129.us-east-2.compute.amazonaws.com:7780/" WHERE path = "web/secure/base_url";'
docker exec shopping_admin /var/www/magento2/bin/magento cache:flush

# Configure GitLab
docker exec gitlab sed -i "s|^external_url.*|external_url 'http://ec2-18-223-217-129.us-east-2.compute.amazonaws.com:8023'|" /etc/gitlab/gitlab.rb
docker exec gitlab gitlab-ctl reconfigure
```

NOTE: local setup related to `webarena` benchmark and `browsergym` environment

## 4. Local Setup (WebArena Homepage) 
```
# Clone repositories
git clone https://github.com/Nid989/webarena

# Setup Homepage
YOUR_ACTUAL_HOSTNAME="ec2-18-223-217-129.us-east-2.compute.amazonaws.com"
YOUR_ACTUAL_HOSTNAME=${YOUR_ACTUAL_HOSTNAME%/}
perl -pi -e "s|<your-server-hostname>|${YOUR_ACTUAL_HOSTNAME}|g" environment_docker/webarena-homepage/templates/index.html
flask run --host=0.0.0.0 --port=4399

# Install Python dependencies
pip install browsergym
pip uninstall playwright
pip install playwright==1.47.0
playwright install chromium
```

## 5. Environment Configuration
```
git clone https://github.com/ServiceNow/BrowserGym 

# API Keys
export OPENAI_API_KEY="your-key-here"

# Service URLs
export SHOPPING="http://ec2-18-223-217-129.us-east-2.compute.amazonaws.com:7770"
export SHOPPING_ADMIN="http://ec2-18-223-217-129.us-east-2.compute.amazonaws.com:7780/admin"
export REDDIT="http://ec2-18-223-217-129.us-east-2.compute.amazonaws.com:9999"
export GITLAB="http://ec2-18-223-217-129.us-east-2.compute.amazonaws.com:8023"
export MAP="http://ec2-18-223-217-129.us-east-2.compute.amazonaws.com:3000"
export WIKIPEDIA="http://ec2-18-223-217-129.us-east-2.compute.amazonaws.com:8888/wikipedia_en_all_maxi_2022-05/A/User:The_other_Kiwix_guy/Landing"
export HOMEPAGE="http://10.15.29.154:4399"  # Update with your local host
```

## 6. Run Demo 
```
python3 demo_agent/run_demo.py --model_name=gpt-4o --task_name=webarena.196
```

Note: If you encounter any issues during setup, please contact me for assistance.