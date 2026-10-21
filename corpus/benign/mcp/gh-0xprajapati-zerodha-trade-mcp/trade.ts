import { KiteConnect } from "kiteconnect";
import * as dotenv from 'dotenv';

// Load environment variables
dotenv.config();

const apiKey = process.env.KITE_API_KEY;
const apiSecret = process.env.KITE_SECRET_KEY;
const requestToken = process.env.REQUEST_TOKEN;
let accessToken = process.env.ACCESS_TOKEN;

if (!apiKey || !apiSecret || !requestToken || !accessToken) {
  throw new Error('Missing required environment variables. Please check your .env file.');
}

const kc = new KiteConnect({ api_key: apiKey as string });
// console.log("login url : ", kc.getLoginURL());
kc.setAccessToken(accessToken as string);

export async function kiteLogin() {
  const response = await kc.generateSession(requestToken as string, apiSecret as string);
  console.log("Session generated:", response);
  kc.setAccessToken(response.access_token);
  accessToken = response.access_token;
  // console.log("access_token : ", response.access_token);
} 

export async function getProfile() {
  try {
    const profile = await kc.getProfile();
    let str = `name : ${profile.user_name}, email : ${profile.email}, mobile : ${profile.user_shortname}, demat_email : ${profile.meta.demat_consent}, demat_mobile : ${profile.meta.demat_consent}, demat_name : ${profile.meta.demat_consent}`
    return str;
  } catch (err) {
    console.error("Error getting profile:", err);
  }
}

// place order on zerodha exchange
export async function placeOrder(symbol: string, quantity: number, type: "BUY" | "SELL") {
  try {
    await kc.placeOrder(
        kc.VARIETY_REGULAR,
        {
            exchange: kc.EXCHANGE_NSE,
            tradingsymbol: symbol,
            transaction_type: type,
            quantity: quantity,
            product: kc.PRODUCT_CNC,
            order_type: kc.ORDER_TYPE_MARKET,
            tag: "test",
        });
  } catch (err) {
    console.error(err);
  }
}

// get the holdings on zerodha exchange
export async function getHoldings() {
  const holdings = await kc.getHoldings();
  let allHoldings= ""
  holdings.map(holding => {
    allHoldings += `stock : ${holding.tradingsymbol}, quantity : ${holding.quantity}, average_price : ${holding.average_price}, last_price : ${holding.last_price}, pnl : ${holding.pnl}\n`  
  })
  return allHoldings;
}

// get the Positions on zerodha exchange
export async function getPositions() {
  const positions = await kc.getPositions();
  let allPositions= ""
  positions.day.map(position => {
    allPositions += `stock : ${position.tradingsymbol}, quantity : ${position.quantity}, average_price : ${position.average_price}, last_price : ${position.last_price}, pnl : ${position.pnl}\n`  
  })
  return allPositions;
}