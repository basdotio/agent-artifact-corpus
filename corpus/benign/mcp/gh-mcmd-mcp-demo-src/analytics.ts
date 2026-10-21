import fetch from 'node-fetch';
import * as dotenv from 'dotenv';

dotenv.config();

const GA4_MEASUREMENT_ID = process.env.GA4_MEASUREMENT_ID;
const GA4_API_SECRET = process.env.GA4_API_SECRET;

export const sendAnalyticsPing = async (eventName: string) => {
    if (!GA4_MEASUREMENT_ID || !GA4_MEASUREMENT_ID.startsWith('G-') || !GA4_API_SECRET || GA4_API_SECRET === 'YOUR_API_SECRET') {
        console.log("Analytics not configured, skipping ping.");
        return;
    }
  try {
    await fetch(`https://www.google-analytics.com/mp/collect?measurement_id=${GA4_MEASUREMENT_ID}&api_secret=${GA4_API_SECRET}`, {
      method: 'POST',
      body: JSON.stringify({
        client_id: 'mcp-server',
        events: [{
          name: eventName,
          params: {},
        }],
      }),
    });
    console.log(`Analytics ping sent for event: ${eventName}`);
  } catch (error) {
    console.error('Error sending analytics ping:', error);
  }
};
