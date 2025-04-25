from aws_cdk import (
    Stack,
    aws_s3 as s3,
)
from aws_cdk.aws_lambda import Runtime
from aws_cdk.aws_lambda_python_alpha import PythonFunction
from cdklabs.generative_ai_cdk_constructs import bedrock
from constructs import Construct


class RetencionStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)
        
        action_group_function1 = PythonFunction(
            self,
            "ActionGroupFunction1",
            entry="./lambda",
            runtime=Runtime.PYTHON_3_12,
            index="function1.py",
            handler="lambda_handler",
        )

        action_group_function2 = PythonFunction(
                self,
                "ActionGroupFunction2",
                entry="./lambda",
                runtime=Runtime.PYTHON_3_12,
                index="function2.py",
                handler="lambda_handler",

        )

        crip =  bedrock.CrossRegionInferenceProfile.from_config(
            geo_region=bedrock.CrossRegionInferenceProfileRegion.US,
            model=bedrock.BedrockFoundationModel.ANTHROPIC_CLAUDE_3_5_HAIKU_V1_0,
        )

        agent = bedrock.Agent(
            self, 
            "RetencionAgent",
            instruction="You are a helpful assistant. Answer the question based on the context.",
            foundation_model=crip,
            should_prepare_agent= True ,
        )

        action_group: bedrock.ActionGroup = bedrock.AgentActionGroup(
            name = "RetencionActionGroup1",
            description="This is an action group 1 for Retencion.",
            executor= bedrock.ActionGroupExecutor.fromlambda_function(lambda_function=action_group_function1),
            enabled=True,
            api_schema=bedrock.ApiSchema.from_local_asset("./lambda/openapi.json"),
        )

        action_group2: bedrock.ActionGroup = bedrock.AgentActionGroup(
            name = "RetencionActionGroup2" ,
            description = "This is action group 2 for Retencion.",
            executor = bedrock.ActionGroupExecutor.fromlambda_function(lambda_function=action_group_function2),
            enabled=True,
            api_schema=bedrock.ApiSchema.from_local_asset("./lambda/openapi2.json"),
        )

        agent.add_action_group(action_group)
        agent.add_action_group(action_group2)
        
        kb = bedrock.VectorKnowledgeBase(
                self, 
                'KnowledgeBase',
                embeddings_model=bedrock.BedrockFoundationModel.TITAN_EMBED_TEXT_V2_1024,
                instruction= 'Use this knowledge base to answer questions about documents.' + 'it contains full documentation',
             )

        docBucket = s3.Bucket(self,'DocBucket')

        bedrock.S3DataSource(
            self,
            'Datasource',
            bucket=docBucket,
            knowledge_base=kb,
            data_source_name='Docs',
            chunking_strategy= bedrock.ChunkingStrategy.FIXED_SIZE,
        )

        agent.add_knowledge_base(kb)

        guard1 = bedrock.Guardrail(
                                    self, 'guard1',
                                    name='guard1',
                                    description= "guardrails legales y eticos."
                                    )

        #guard1.add_content_filter(
        #    type=ContentFilterType.SEXUAL,
        #    input_strength=ContentFilterStrength.HIGH,
        #    output_strength=ContentFilterStrength.MEDIUM,
        #    input_modalities=[ModalityType.TEXT, ModalityType.IMAGE],
        #    output_modalities=[ModalityType.TEXT],
        #);

        # Add PII filter for addresses
        guard1.add_pii_filter(
            type= bedrock.pii_type.General.ADDRESS,
            action= bedrock.GuardrailAction.ANONYMIZE,
        )

        # Add PII filter for credit card numbers
        guard1.add_pii_filter(
            type= bedrock.pii_type.Finance.CREDIT_DEBIT_CARD_NUMBER,
            action= bedrock.GuardrailAction.ANONYMIZE,
        )

        agent.add_guardrail(guard1)


