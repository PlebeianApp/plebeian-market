import { browser } from "$app/env";

export let SATS_IN_BTC = 100000000;

export function isDevelopment() {
    return import.meta.env.MODE === 'development';
}

export function isStaging() {
    return import.meta.env.MODE === 'staging';
}

export function isProduction() {
    return import.meta.env.MODE === 'production';
}

export function getBaseUrl() {
    return import.meta.env.VITE_BASE_URL;
}

export function getApiBaseUrl() {
    return import.meta.env.VITE_API_BASE_URL;
}

export function getEnvironmentInfo() {
    return import.meta.env.MODE;
}

export function sats2usd(sats: number, btc2usd: number | null): number | null {
    if (btc2usd === null) {
        return null;
    } else {
        return sats / SATS_IN_BTC * btc2usd;
    }
}

export function usd2sats(usd: number, btc2usd: number | null): number | null {
    if (btc2usd === null) {
        return null;
    } else {
        return usd / btc2usd * SATS_IN_BTC;
    }
}

export function formatBTC(sats: number) {
    return (1 / SATS_IN_BTC * sats).toFixed(9);
}
