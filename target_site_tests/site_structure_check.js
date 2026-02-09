// JavaScript for checking website structure
const axios = require('axios');
const cheerio = require('cheerio');

async function checkSiteStructure(url) {
    try {
        const response = await axios.get(url);
        const $ = cheerio.load(response.data);

        let structure = [];
        $('a').each((index, element) => {
            structure.push({
                text: $(element).text().trim(),
                href: $(element).attr('href')
            });
        });

        console.log('Site structure:', JSON.stringify(structure, null, 2));
    } catch (error) {
        console.error('Error fetching site:', error.message);
    }
}

const targetSite = process.argv[2] || 'https://example.com';
checkSiteStructure(targetSite);