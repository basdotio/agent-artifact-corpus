import https from 'https';
import { parseStringPromise } from 'xml2js';

/**
 * Namecheap API client for domain availability checking
 */
export class NamecheapClient {
  constructor(config) {
    this.apiUser = config.apiUser;
    this.apiKey = config.apiKey;
    this.username = config.username;
    this.clientIp = config.clientIp;
    this.sandbox = config.sandbox || false;
    this.affiliateId = config.affiliateId || 'boomexchange'; // Default affiliate code

    this.baseUrl = this.sandbox
      ? 'api.sandbox.namecheap.com'
      : 'api.namecheap.com';
  }

  /**
   * Generate purchase URL with affiliate tracking
   * @param {string} domain - Domain name
   * @returns {string} - Purchase URL with affiliate code
   */
  getPurchaseUrl(domain) {
    // Impact affiliate tracking format
    // Uses utm_campaign from Impact dashboard + standard Namecheap params
    const params = new URLSearchParams({
      domain: domain,
      afsrc: '1',
      utm_source: 'IR',
      utm_medium: 'Affiliate',
      utm_campaign: this.affiliateId || '7069952',
      affnetwork: 'ir'
    });
    return `https://www.namecheap.com/domains/registration/results/?${params.toString()}`;
  }

  /**
   * Demo mode - returns mock data for testing
   * @param {string[]} domains - Array of domain names
   * @returns {Object} - Mock availability data
   */
  getMockData(domains) {
    const results = {};
    for (const domain of domains) {
      // Simulate realistic availability (70% taken, 20% available, 10% premium)
      const random = Math.random();
      if (random < 0.7) {
        results[domain] = {
          available: false,
          premium: false,
          price: null,
          purchaseUrl: this.getPurchaseUrl(domain)
        };
      } else if (random < 0.9) {
        results[domain] = {
          available: true,
          premium: false,
          price: null,
          purchaseUrl: this.getPurchaseUrl(domain)
        };
      } else {
        results[domain] = {
          available: true,
          premium: true,
          price: '$2,500',
          purchaseUrl: this.getPurchaseUrl(domain)
        };
      }
    }
    return results;
  }

  /**
   * Check domain availability for multiple domains
   * @param {string[]} domains - Array of domain names
   * @returns {Promise<Object>} - Map of domain to availability (true = available)
   */
  async checkDomains(domains) {
    if (!Array.isArray(domains) || domains.length === 0) {
      throw new Error('domains must be a non-empty array');
    }

    // Demo mode - return mock data if no API key
    if (!this.apiKey || this.apiKey === 'demo') {
      return this.getMockData(domains);
    }

    const domainList = domains.join(',');
    const params = new URLSearchParams({
      ApiUser: this.apiUser,
      ApiKey: this.apiKey,
      UserName: this.username,
      ClientIp: this.clientIp,
      Command: 'namecheap.domains.check',
      DomainList: domainList
    });

    const url = `https://${this.baseUrl}/xml.response?${params}`;

    return new Promise((resolve, reject) => {
      https.get(url, (res) => {
        let data = '';

        res.on('data', (chunk) => {
          data += chunk;
        });

        res.on('end', async () => {
          try {
            const result = await this.parseResponse(data);
            resolve(result);
          } catch (error) {
            reject(error);
          }
        });
      }).on('error', (error) => {
        reject(error);
      });
    });
  }

  /**
   * Parse XML response from Namecheap API
   * @param {string} xml - XML response
   * @returns {Promise<Object>} - Parsed availability data
   */
  async parseResponse(xml) {
    const parsed = await parseStringPromise(xml);
    const response = parsed.ApiResponse;

    // Check for errors
    if (response.$.Status === 'ERROR') {
      const error = response.Errors[0].Error[0];
      throw new Error(`Namecheap API Error ${error.$.Number}: ${error._}`);
    }

    // Parse domain check results
    const commandResponse = response.CommandResponse[0];
    const domainCheckResult = commandResponse.DomainCheckResult;

    const results = {};

    for (const domain of domainCheckResult) {
      const domainName = domain.$.Domain;
      const available = domain.$.Available === 'true';
      const isPremium = domain.$.IsPremiumName === 'true';
      const premiumPrice = domain.$.PremiumRegistrationPrice;

      results[domainName] = {
        available,
        premium: isPremium,
        price: premiumPrice || null,
        purchaseUrl: this.getPurchaseUrl(domainName)
      };
    }

    return results;
  }
}

/**
 * Convenience function for checking domains
 * @param {string[]} domains - Array of domain names
 * @returns {Promise<Object>} - Availability map
 */
export async function checkDomains(domains) {
  const client = new NamecheapClient({
    apiUser: process.env.NAMECHEAP_API_USER,
    apiKey: process.env.NAMECHEAP_API_KEY,
    username: process.env.NAMECHEAP_USERNAME,
    clientIp: process.env.NAMECHEAP_CLIENT_IP,
    sandbox: process.env.NAMECHEAP_SANDBOX === 'true'
  });

  const results = await client.checkDomains(domains);

  // Simplify to just availability
  const simplified = {};
  for (const [domain, data] of Object.entries(results)) {
    simplified[domain] = data.available;
  }

  return simplified;
}
