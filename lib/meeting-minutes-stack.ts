import * as cdk from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as s3 from 'aws-cdk-lib/aws-s3';

export class MeetingMinutesStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const bedrockModelId = this.node.tryGetContext('bedrockModelId');
    const allowedOrigins = this.node.tryGetContext('allowedOrigins') ?? ['http://localhost:3000'];

    const storageBucket = new s3.Bucket(this, 'MinutesBucket', {
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      enforceSSL: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    const minutesFunction = new lambda.Function(this, 'MinutesFunction', {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'index.handler',
      code: lambda.Code.fromAsset('lambda/minutes'),
      timeout: cdk.Duration.seconds(90),
      memorySize: 512,
      logRetention: logs.RetentionDays.ONE_WEEK,
      environment: {
        MINUTES_BUCKET: storageBucket.bucketName,
        BEDROCK_MODEL_ID: bedrockModelId,
        ALLOWED_ORIGINS: JSON.stringify(allowedOrigins),
      },
    });

    storageBucket.grantReadWrite(minutesFunction);
    minutesFunction.addToRolePolicy(new iam.PolicyStatement({
      actions: ['bedrock:InvokeModel'],
      resources: [
        `arn:aws:bedrock:${this.region}::foundation-model/*`,
        `arn:aws:bedrock:${this.region}:${this.account}:inference-profile/*`,
      ],
    }));

    const api = new apigateway.RestApi(this, 'Api', {
      restApiName: 'meeting-minutes-api',
      defaultCorsPreflightOptions: {
        allowOrigins: allowedOrigins,
        allowMethods: ['OPTIONS', 'GET', 'POST'],
        allowHeaders: ['Content-Type', 'Authorization'],
      },
    });

    const minutes = api.root.addResource('minutes');
    minutes.addMethod('POST', new apigateway.LambdaIntegration(minutesFunction));
    minutes.addResource('{id}').addMethod('GET', new apigateway.LambdaIntegration(minutesFunction));

    new cdk.CfnOutput(this, 'ApiUrl', {
      value: api.url,
    });
  }
}

