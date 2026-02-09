// Script for testing different data sources
const axios = require('axios');

async function testDataSource(url) {
    try {
        const response = await axios.get(url);
        console.log(`Data from ${url}:`, response.data.slice(0, 200)); // Output small preview
    } catch (error) {
        console.error(`Error with ${url}:`, error.message);
    }
}

const dataSources = [
    'https://jsonplaceholder.typicode.com/posts',
    'https://jsonplaceholder.typicode.com/comments',
    'https://jsonplaceholder.typicode.com/albums'
];

dataSources.forEach(source => testDataSource(source));