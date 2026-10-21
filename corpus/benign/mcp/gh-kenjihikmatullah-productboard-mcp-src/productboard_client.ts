class ProductboardClient {
    private accessToken: string
    private baseUrl = "https://api.productboard.com"
    private headers: { [key: string]: string };

    constructor(accessToken: string) {
        this.accessToken = accessToken
        this.headers = {
            Authorization: `Bearer ${this.accessToken}`,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "X-Version": "1",
        };
    }

    async get(endpoint: string) {
        const response = await fetch(`${this.baseUrl}${endpoint}`, {
            method: "GET",
            headers: this.headers,
        });
        return response.json()
    }
}

const productboardAccessToken = process.env.PRODUCTBOARD_ACCESS_TOKEN

if (!productboardAccessToken) {
    console.error("Please set PRODUCTBOARD_ACCESS_TOKEN environment variable");
    process.exit(1);
}

const productboardClient = new ProductboardClient(process.env.PRODUCTBOARD_ACCESS_TOKEN!)
export default productboardClient
