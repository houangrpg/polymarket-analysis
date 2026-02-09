const axios = require('axios');

async function validateDeployment(url) {
    console.log(`Validating deployment at: ${url}`);
    try {
        const startTime = Date.now();
        const response = await axios.get(url, {
            headers: {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        });
        const duration = Date.now() - startTime;

        if (response.status === 200) {
            console.log('✅ Status: 200 OK');
        } else {
            console.error(`❌ Status: ${response.status}`);
            process.exit(1);
        }

        // Basic CDN check (looking for common headers)
        const cdnHeaders = ['x-cache', 'cf-ray', 'x-fastly-request-id', 'x-amz-cf-id', 'server'];
        console.log('Headers check:');
        cdnHeaders.forEach(header => {
            if (response.headers[header]) {
                console.log(`  - ${header}: ${response.headers[header]}`);
            }
        });

        if (response.data.includes('html') || response.data.includes('body')) {
            console.log('✅ Content: HTML detected');
        } else {
            console.error('❌ Content: HTML not found in response');
            process.exit(1);
        }

        console.log(`⏱️ Response time: ${duration}ms`);
        console.log('🚀 Deployment validation successful!');
    } catch (error) {
        console.error('❌ Validation failed:', error.message);
        process.exit(1);
    }
}

const targetUrl = process.argv[2];
if (!targetUrl) {
    console.error('Usage: node validate_deployment.js <URL>');
    process.exit(1);
}

validateDeployment(targetUrl);
